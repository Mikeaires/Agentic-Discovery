"""Discovery modules — one per use case, all running on the same engine.

A module is just: an Ontology (the goal + coverage rules) + synthesizers (graph
-> deliverables) + an optional offline demo script. Process discovery is fully
built; AI-use-case and architecture discovery are real ontologies wired the
same way, to prove the engine generalises without change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..graph import GraphDelta, KnowledgeGraph
from ..ontology import Ontology


@dataclass
class DemoScript:
    """Aligned canned answers + extracted deltas for the offline demo."""

    answers: list[str]
    deltas: list[GraphDelta]


@dataclass
class DiscoveryModule:
    name: str
    title: str
    ontology: Ontology
    synthesize: Callable[[KnowledgeGraph], dict[str, str]]
    demo: DemoScript | None = None


from . import process_discovery, ai_usecase_discovery, architecture_discovery  # noqa: E402

REGISTRY: dict[str, DiscoveryModule] = {
    m.name: m for m in (
        process_discovery.MODULE,
        ai_usecase_discovery.MODULE,
        architecture_discovery.MODULE,
    )
}


def get(name: str) -> DiscoveryModule:
    if name not in REGISTRY:
        raise KeyError(f"unknown module '{name}'. Available: {', '.join(REGISTRY)}")
    return REGISTRY[name]
