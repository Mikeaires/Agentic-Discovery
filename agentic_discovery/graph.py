"""Provenance-aware knowledge graph — the engine's state and memory.

Every node and edge carries the claims that asserted it: who said it, when, the
verbatim quote, and a confidence. Two interviewees can disagree about the same
node without one overwriting the other — the node holds both claims and the
critic surfaces the conflict. This is what makes the discovery "grounded".
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict


def _slug(*parts: str) -> str:
    return "::".join(p.strip().lower() for p in parts if p is not None)


@dataclass
class Claim:
    """A single (source -> assertion) pair. The unit of provenance."""

    source: str  # interviewee id / name
    session_id: str
    value: str  # what was asserted (label, attribute value, or "exists")
    confidence: float = 0.6
    quote: str = ""  # verbatim words the claim was drawn from
    timestamp: float = field(default_factory=time.time)


@dataclass
class Node:
    id: str
    type: str
    label: str
    attributes: dict[str, str] = field(default_factory=dict)
    claims: list[Claim] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        return max((c.confidence for c in self.claims), default=0.0)

    @property
    def sources(self) -> set[str]:
        return {c.source for c in self.claims}


@dataclass
class Edge:
    id: str
    type: str
    source: str  # node id
    target: str  # node id
    attributes: dict[str, str] = field(default_factory=dict)
    claims: list[Claim] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        return max((c.confidence for c in self.claims), default=0.0)


# --- Extractor output: assertions reference entities by (type, label) ---------
# The extractor doesn't know node ids; it speaks in terms of what the person
# said. The graph resolves assertions to nodes, creating or merging as needed.


@dataclass
class NodeAssertion:
    type: str
    label: str
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class EdgeAssertion:
    type: str
    source_type: str
    source_label: str
    target_type: str
    target_label: str


@dataclass
class GraphDelta:
    """A batch of assertions extracted from one answer, sharing provenance."""

    nodes: list[NodeAssertion] = field(default_factory=list)
    edges: list[EdgeAssertion] = field(default_factory=list)


class KnowledgeGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, Edge] = {}

    # -- lookup ---------------------------------------------------------------
    def node_id(self, type_: str, label: str) -> str:
        return _slug(type_, label)

    def find(self, type_: str, label: str) -> Node | None:
        return self.nodes.get(self.node_id(type_, label))

    def nodes_of_type(self, type_: str) -> list[Node]:
        return [n for n in self.nodes.values() if n.type == type_]

    def edges_from(self, node_id: str, type_: str | None = None) -> list[Edge]:
        return [
            e
            for e in self.edges.values()
            if e.source == node_id and (type_ is None or e.type == type_)
        ]

    def edges_to(self, node_id: str, type_: str | None = None) -> list[Edge]:
        return [
            e
            for e in self.edges.values()
            if e.target == node_id and (type_ is None or e.type == type_)
        ]

    # -- mutation -------------------------------------------------------------
    def upsert_node(self, type_: str, label: str, claim: Claim,
                    attributes: dict[str, str] | None = None) -> Node:
        nid = self.node_id(type_, label)
        node = self.nodes.get(nid)
        if node is None:
            node = Node(id=nid, type=type_, label=label)
            self.nodes[nid] = node
        node.claims.append(claim)
        for k, v in (attributes or {}).items():
            # Keep the first asserted value; record competing values as claims
            # so contradictions remain visible rather than being overwritten.
            if k not in node.attributes:
                node.attributes[k] = v
            elif node.attributes[k] != v:
                node.claims.append(Claim(
                    source=claim.source, session_id=claim.session_id,
                    value=f"{k}={v}", confidence=claim.confidence,
                    quote=claim.quote))
        return node

    def upsert_edge(self, type_: str, source_id: str, target_id: str,
                    claim: Claim) -> Edge:
        eid = _slug(type_, source_id, target_id)
        edge = self.edges.get(eid)
        if edge is None:
            edge = Edge(id=eid, type=type_, source=source_id, target=target_id)
            self.edges[eid] = edge
        edge.claims.append(claim)
        return edge

    def apply(self, delta: GraphDelta, source: str, session_id: str) -> int:
        """Apply an extracted delta with shared provenance. Returns #assertions."""
        applied = 0
        for na in delta.nodes:
            self.upsert_node(
                na.type, na.label,
                Claim(source=source, session_id=session_id, value="exists"),
                na.attributes)
            applied += 1
        for ea in delta.edges:
            # Ensure endpoints exist (an edge can introduce a new node).
            self.upsert_node(ea.source_type, ea.source_label,
                             Claim(source, session_id, "exists"))
            self.upsert_node(ea.target_type, ea.target_label,
                             Claim(source, session_id, "exists"))
            self.upsert_edge(
                ea.type,
                self.node_id(ea.source_type, ea.source_label),
                self.node_id(ea.target_type, ea.target_label),
                Claim(source, session_id, "exists"))
            applied += 1
        return applied

    # -- contradictions -------------------------------------------------------
    def contradictions(self) -> list[tuple[Node, str, list[str]]]:
        """Nodes whose attribute was asserted with conflicting values."""
        out: list[tuple[Node, str, list[str]]] = []
        for node in self.nodes.values():
            by_attr: dict[str, set[str]] = {}
            for c in node.claims:
                if c.value.startswith(("=", )) or "=" not in c.value:
                    continue
                key, _, val = c.value.partition("=")
                by_attr.setdefault(key, set()).add(val)
            for key, vals in by_attr.items():
                base = node.attributes.get(key)
                allvals = vals | ({base} if base else set())
                if len(allvals) > 1:
                    out.append((node, key, sorted(allvals)))
        return out

    # -- persistence ----------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "nodes": [asdict(n) for n in self.nodes.values()],
            "edges": [asdict(e) for e in self.edges.values()],
        }

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGraph":
        g = cls()
        for n in data.get("nodes", []):
            claims = [Claim(**c) for c in n.get("claims", [])]
            g.nodes[n["id"]] = Node(
                id=n["id"], type=n["type"], label=n["label"],
                attributes=n.get("attributes", {}), claims=claims)
        for e in data.get("edges", []):
            claims = [Claim(**c) for c in e.get("claims", [])]
            g.edges[e["id"]] = Edge(
                id=e["id"], type=e["type"], source=e["source"],
                target=e["target"], attributes=e.get("attributes", {}),
                claims=claims)
        return g
