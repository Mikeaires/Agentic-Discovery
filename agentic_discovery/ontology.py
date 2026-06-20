"""Target ontology + coverage logic — the goal, made computable.

An ontology is the *definition of done* for a discovery type: the entity and
relation types we want instantiated, and the requirements that say when an
entity is sufficiently described. Coverage over those requirements is what
drives the planner ("ask about the biggest hole") and the critic ("are we
done"). Adding a new use case = adding an Ontology + synthesizers; the engine
is unchanged. This is the scalability boundary of the whole system.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .graph import KnowledgeGraph, Node


@dataclass
class EntityType:
    name: str
    description: str = ""
    attributes: list[str] = field(default_factory=list)


@dataclass
class RelationType:
    name: str
    source_types: list[str]
    target_types: list[str]
    description: str = ""


@dataclass
class RequiredRelation:
    """Every entity of `subject_type` should have >= `minimum` `relation` edges.

    direction="out": subject is the edge source. "in": subject is the target.
    """

    subject_type: str
    relation: str
    direction: str = "out"  # "out" | "in"
    minimum: int = 1
    description: str = ""
    severity: float = 1.0


@dataclass
class RequiredAttribute:
    subject_type: str
    attribute: str
    description: str = ""
    severity: float = 0.6


@dataclass
class Gap:
    """A specific, valuable hole in the graph — the planner ranks these."""

    kind: str  # "anchor" | "relation" | "attribute"
    description: str  # human objective, e.g. "who performs step 'Approve invoice'?"
    subject_type: str
    subject_label: str | None  # None for an anchor (no entity yet)
    severity: float
    relation: str | None = None
    attribute: str | None = None

    def key(self) -> str:
        return f"{self.kind}:{self.subject_type}:{self.subject_label}:{self.relation or self.attribute}"


@dataclass
class CoverageReport:
    satisfied: int
    total: int
    gaps: list[Gap]

    @property
    def ratio(self) -> float:
        return 1.0 if self.total == 0 else self.satisfied / self.total


@dataclass
class Ontology:
    name: str
    description: str
    anchor_type: str  # the entity the discovery is "about" (e.g. Step / UseCase)
    entity_types: list[EntityType] = field(default_factory=list)
    relation_types: list[RelationType] = field(default_factory=list)
    required_relations: list[RequiredRelation] = field(default_factory=list)
    required_attributes: list[RequiredAttribute] = field(default_factory=list)
    opening_objective: str = "Give me a high-level walkthrough to start."

    def entity(self, name: str) -> EntityType | None:
        return next((e for e in self.entity_types if e.name == name), None)


def compute_coverage(graph: KnowledgeGraph, ontology: Ontology) -> CoverageReport:
    """Evaluate every requirement against every relevant entity in the graph."""
    gaps: list[Gap] = []
    satisfied = 0
    total = 0

    anchors = graph.nodes_of_type(ontology.anchor_type)
    if not anchors:
        # Nothing discovered yet — the one opening gap dominates.
        gaps.append(Gap(
            kind="anchor", description=ontology.opening_objective,
            subject_type=ontology.anchor_type, subject_label=None,
            severity=5.0))
        return CoverageReport(satisfied=0, total=1, gaps=gaps)

    for req in ontology.required_relations:
        for node in graph.nodes_of_type(req.subject_type):
            total += 1
            edges = (graph.edges_from(node.id, req.relation)
                     if req.direction == "out"
                     else graph.edges_to(node.id, req.relation))
            if len(edges) >= req.minimum:
                satisfied += 1
            else:
                gaps.append(Gap(
                    kind="relation",
                    description=_relation_objective(req, node),
                    subject_type=req.subject_type, subject_label=node.label,
                    relation=req.relation,
                    severity=req.severity * _centrality(graph, node)))

    for req in ontology.required_attributes:
        for node in graph.nodes_of_type(req.subject_type):
            total += 1
            if req.attribute in node.attributes:
                satisfied += 1
            else:
                gaps.append(Gap(
                    kind="attribute",
                    description=(f"What is the {req.attribute} of "
                                 f"{req.subject_type.lower()} '{node.label}'?"),
                    subject_type=req.subject_type, subject_label=node.label,
                    attribute=req.attribute, severity=req.severity))

    # Low-confidence anchors are worth re-asking (triangulation).
    for node in anchors:
        if 0 < node.confidence < 0.4:
            gaps.append(Gap(
                kind="attribute",
                description=(f"You mentioned '{node.label}' only in passing — "
                             f"can you confirm and expand on it?"),
                subject_type=node.type, subject_label=node.label,
                attribute="_confidence", severity=0.5))

    return CoverageReport(satisfied=satisfied, total=max(total, 1), gaps=gaps)


def _relation_objective(req: RequiredRelation, node: Node) -> str:
    verb = req.description or f"{req.relation} relationship"
    return f"For {req.subject_type.lower()} '{node.label}': {verb}"


def _centrality(graph: KnowledgeGraph, node: Node) -> float:
    """More-connected unknowns unlock more of the graph — rank them higher."""
    degree = len(graph.edges_from(node.id)) + len(graph.edges_to(node.id))
    return 1.0 + 0.15 * degree
