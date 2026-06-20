"""The reasoning roles around the graph: planner, question-generator, extractor.

`Brain` is the seam between the deterministic engine and the model. The engine
computes *which holes exist* (pure, in ontology.compute_coverage); the brain
decides *which hole is most worth asking about*, *how to ask it warmly*, and
*how to turn the answer into graph structure*. Two implementations:

  MockBrain   — deterministic, offline; drives tests and the canned demo.
  ClaudeBrain — real reasoning via claude-opus-4-8.

Both share the engine's gap logic, so swapping brains never changes what
"coverage" or "done" means — only the quality of questions and extraction.
"""

from __future__ import annotations

from typing import Protocol

from .graph import GraphDelta, KnowledgeGraph, NodeAssertion, EdgeAssertion
from .ontology import Gap, Ontology


class Brain(Protocol):
    def rank_gaps(self, gaps: list[Gap], graph: KnowledgeGraph,
                  ontology: Ontology) -> Gap: ...

    def compose_question(self, gap: Gap, graph: KnowledgeGraph,
                         history: list[tuple[str, str]]) -> str: ...

    def extract(self, answer: str, gap: Gap, graph: KnowledgeGraph,
                ontology: Ontology) -> GraphDelta: ...


# --------------------------------------------------------------------------- #
# Deterministic brain — no model, no network. Realism comes from ClaudeBrain;  #
# this exists to exercise the loop, coverage, and stopping logic for real.     #
# --------------------------------------------------------------------------- #
class MockBrain:
    def __init__(self, scripted: list[GraphDelta] | None = None) -> None:
        # Each extract() pops the next scripted delta, regardless of the answer
        # text — enough to fill the graph deterministically across turns.
        self._scripted = list(scripted or [])

    def rank_gaps(self, gaps, graph, ontology) -> Gap:
        return max(gaps, key=lambda g: g.severity)

    def compose_question(self, gap, graph, history) -> str:
        return gap.description

    def extract(self, answer, gap, graph, ontology) -> GraphDelta:
        if self._scripted:
            return self._scripted.pop(0)
        return GraphDelta()


# --------------------------------------------------------------------------- #
# Claude brain — the real planner / question-generator / extractor.            #
# --------------------------------------------------------------------------- #
_EXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "type": {"type": "string"},
                    "label": {"type": "string"},
                    "attributes": {"type": "object", "additionalProperties": {"type": "string"}},
                },
                "required": ["type", "label", "attributes"],
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "type": {"type": "string"},
                    "source_type": {"type": "string"},
                    "source_label": {"type": "string"},
                    "target_type": {"type": "string"},
                    "target_label": {"type": "string"},
                },
                "required": ["type", "source_type", "source_label",
                             "target_type", "target_label"],
            },
        },
    },
    "required": ["nodes", "edges"],
}


class ClaudeBrain:
    def __init__(self, llm=None) -> None:
        if llm is None:
            from .llm import ClaudeLLM
            llm = ClaudeLLM()
        self.llm = llm

    def rank_gaps(self, gaps, graph, ontology) -> Gap:
        top = sorted(gaps, key=lambda g: g.severity, reverse=True)[:6]
        if len(top) == 1:
            return top[0]
        listing = "\n".join(f"{i}. {g.description} (severity {g.severity:.1f})"
                            for i, g in enumerate(top))
        schema = {"type": "object", "additionalProperties": False,
                  "properties": {"choice": {"type": "integer"}},
                  "required": ["choice"]}
        try:
            out = self.llm.json(
                system=(f"You are planning a {ontology.name} discovery interview. "
                        "Pick the single most valuable thing to ask about next: "
                        "the gap that is most central, most blocking, or unlocks "
                        "the most downstream understanding."),
                prompt=f"Open gaps:\n{listing}\n\nReturn the index of the best one.",
                schema=schema)
            return top[int(out["choice"]) % len(top)]
        except Exception:
            return top[0]

    def compose_question(self, gap, graph, history) -> str:
        recent = "\n".join(f"Q: {q}\nA: {a}" for q, a in history[-3:])
        return self.llm.text(
            system=("You are a warm, sharp discovery interviewer. Ask ONE clear, "
                    "natural question that gets the information described. Adapt to "
                    "what was already said; don't repeat. Let the person ramble if "
                    "it's productive. No preamble — just the question."),
            prompt=(f"Recent exchange:\n{recent or '(start of interview)'}\n\n"
                    f"Objective: {gap.description}\n\nYour question:"))

    def extract(self, answer, gap, graph, ontology) -> GraphDelta:
        ents = ", ".join(e.name for e in ontology.entity_types)
        rels = "\n".join(f"- {r.name}: {r.source_types} -> {r.target_types}"
                         for r in ontology.relation_types)
        out = self.llm.json(
            system=(f"You extract a {ontology.name} knowledge graph from interview "
                    "answers. Emit only what the person actually said — do not "
                    f"invent. Entity types: {ents}.\nRelation types:\n{rels}\n"
                    "Reuse exact labels of things already mentioned so they merge."),
            prompt=(f"Question asked: {gap.description}\n"
                    f"Answer: {answer}\n\nExtract nodes and edges."),
            schema=_EXTRACT_SCHEMA)
        return GraphDelta(
            nodes=[NodeAssertion(n["type"], n["label"], n.get("attributes", {}))
                   for n in out.get("nodes", [])],
            edges=[EdgeAssertion(e["type"], e["source_type"], e["source_label"],
                                 e["target_type"], e["target_label"])
                   for e in out.get("edges", [])])
