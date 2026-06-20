"""Module #2 (stub): company-wide AI use-case discovery.

Same engine, different ontology. Wired and runnable; synthesizers are minimal
for now. Proves the loop generalises beyond process mapping.
"""

from __future__ import annotations

from ..graph import KnowledgeGraph
from ..ontology import (
    EntityType, Ontology, RelationType, RequiredRelation,
)

ONTOLOGY = Ontology(
    name="AI use-case landscape",
    description="Where AI could create value, grounded in real goals and pains.",
    anchor_type="UseCase",
    entity_types=[
        EntityType("UseCase", "A candidate AI application"),
        EntityType("BusinessGoal", "An outcome the org cares about"),
        EntityType("Process", "A workflow that could be improved"),
        EntityType("PainPoint", "Friction worth removing"),
        EntityType("DataSource", "Data the use-case would need"),
        EntityType("Stakeholder", "Who owns or sponsors it"),
        EntityType("Constraint", "Regulatory / technical / org limit"),
    ],
    relation_types=[
        RelationType("supports", ["UseCase"], ["BusinessGoal"], "goal it advances"),
        RelationType("addresses", ["UseCase"], ["PainPoint"], "pain it removes"),
        RelationType("needs_data", ["UseCase"], ["DataSource"], "data required"),
        RelationType("sponsored_by", ["UseCase"], ["Stakeholder"], "owner"),
        RelationType("limited_by", ["UseCase"], ["Constraint"], "constraint"),
        RelationType("has_pain", ["Process"], ["PainPoint"], "pain in a process"),
    ],
    required_relations=[
        RequiredRelation("UseCase", "supports", "out", 1,
                         "which business goal does this serve?", severity=1.4),
        RequiredRelation("UseCase", "addresses", "out", 1,
                         "what pain does it remove?", severity=1.2),
        RequiredRelation("UseCase", "needs_data", "out", 1,
                         "what data would it need, and do we have it?", severity=1.0),
    ],
    opening_objective=(
        "What business outcomes are you hoping AI could improve — and where does "
        "the work hurt most today?"),
)


def synthesize(graph: KnowledgeGraph) -> dict[str, str]:
    lines = ["# AI use-case landscape (draft)\n"]
    for uc in graph.nodes_of_type("UseCase"):
        lines.append(f"## {uc.label}")
        for rel, lbl in [("supports", "Goal"), ("addresses", "Pain"),
                         ("needs_data", "Data"), ("sponsored_by", "Sponsor")]:
            vals = [graph.nodes[e.target].label
                    for e in graph.edges_from(uc.id, rel) if e.target in graph.nodes]
            if vals:
                lines.append(f"- **{lbl}:** {', '.join(vals)}")
        lines.append("")
    if not graph.nodes_of_type("UseCase"):
        lines.append("_No use cases captured yet._")
    return {"ai-use-case-landscape.md": "\n".join(lines)}


def _build_module():
    from . import DiscoveryModule
    return DiscoveryModule(
        name="ai-usecases",
        title="Company-wide AI use-case discovery (stub)",
        ontology=ONTOLOGY,
        synthesize=synthesize,
        demo=None)


MODULE = _build_module()
