"""Module #3 (stub): data & AI platform / architecture discovery.

Same engine, a layered-architecture ontology. Multi-interviewee maturity
scoring builds on this later; for now it proves the third use case plugs in.
"""

from __future__ import annotations

from ..graph import KnowledgeGraph
from ..ontology import (
    EntityType, Ontology, RelationType, RequiredRelation,
)

ONTOLOGY = Ontology(
    name="platform architecture",
    description="The components of a company's data & AI platform, by layer.",
    anchor_type="Component",
    entity_types=[
        EntityType("Component", "A system or service in the platform"),
        EntityType("Layer", "Ingestion / storage / modeling / serving / governance / ..."),
        EntityType("DataStore", "Where data lives"),
        EntityType("Integration", "A connection to another system"),
        EntityType("Team", "Who owns the component"),
        EntityType("Capability", "What it enables"),
        EntityType("Risk", "A weakness, gap, or single point of failure"),
    ],
    relation_types=[
        RelationType("in_layer", ["Component"], ["Layer"], "architectural layer"),
        RelationType("depends_on", ["Component"], ["Component"], "upstream dependency"),
        RelationType("stores", ["Component"], ["DataStore"], "data it owns"),
        RelationType("integrates", ["Component"], ["Integration"], "connection"),
        RelationType("owned_by", ["Component"], ["Team"], "owning team"),
        RelationType("has_risk", ["Component"], ["Risk"], "known weakness"),
    ],
    required_relations=[
        RequiredRelation("Component", "in_layer", "out", 1,
                         "which layer does this sit in?", severity=1.3),
        RequiredRelation("Component", "owned_by", "out", 1,
                         "which team owns it?", severity=1.1),
    ],
    opening_objective=(
        "Give me the lay of the land — what are the major systems in your data & "
        "AI platform, and roughly what does each one do?"),
)


def synthesize(graph: KnowledgeGraph) -> dict[str, str]:
    by_layer: dict[str, list[str]] = {}
    for comp in graph.nodes_of_type("Component"):
        layers = [graph.nodes[e.target].label
                  for e in graph.edges_from(comp.id, "in_layer")
                  if e.target in graph.nodes] or ["(unplaced)"]
        for layer in layers:
            by_layer.setdefault(layer, []).append(comp.label)
    lines = ["# Platform architecture (draft map)\n"]
    for layer, comps in by_layer.items():
        lines.append(f"## {layer}")
        lines.extend(f"- {c}" for c in comps)
        lines.append("")
    if not by_layer:
        lines.append("_No components captured yet._")
    return {"architecture-map.md": "\n".join(lines)}


def _build_module():
    from . import DiscoveryModule
    return DiscoveryModule(
        name="architecture",
        title="Data & AI platform / architecture discovery (stub)",
        ontology=ONTOLOGY,
        synthesize=synthesize,
        demo=None)


MODULE = _build_module()
