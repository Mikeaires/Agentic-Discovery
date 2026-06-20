"""The discovery loop — the heart of the system.

Each turn: compute the graph's gaps (pure), let the brain pick the most
valuable one and phrase it, ask the human, extract their answer back into the
graph with provenance, and check whether we're done. The graph is both the
state and the control structure: it tells the loop where its biggest hole is.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .brain import Brain
from .channels import InteractionChannel
from .graph import KnowledgeGraph
from .ontology import Ontology, compute_coverage


@dataclass
class InterviewResult:
    graph: KnowledgeGraph
    history: list[tuple[str, str]]
    coverage_trace: list[float]
    stop_reason: str
    contradictions: list[tuple] = field(default_factory=list)


class DiscoveryEngine:
    def __init__(
        self,
        ontology: Ontology,
        brain: Brain,
        channel: InteractionChannel,
        interviewee: str = "anon",
        session_id: str | None = None,
        graph: KnowledgeGraph | None = None,
        coverage_target: float = 0.85,
        max_turns: int = 40,
        patience: int = 4,
    ) -> None:
        self.ontology = ontology
        self.brain = brain
        self.channel = channel
        self.interviewee = interviewee
        self.session_id = session_id or f"sess-{int(time.time())}"
        self.graph = graph or KnowledgeGraph()
        self.coverage_target = coverage_target
        self.max_turns = max_turns
        self.patience = patience

    def run(self) -> InterviewResult:
        history: list[tuple[str, str]] = []
        trace: list[float] = []
        exhausted: set[str] = set()
        stale = 0
        stop_reason = "max_turns"

        for _ in range(self.max_turns):
            report = compute_coverage(self.graph, self.ontology)
            trace.append(round(report.ratio, 3))

            live = [g for g in report.gaps if g.key() not in exhausted]
            has_anchor = bool(self.graph.nodes_of_type(self.ontology.anchor_type))

            if not live:
                stop_reason = "graph complete — no open gaps"
                break
            if has_anchor and report.ratio >= self.coverage_target:
                stop_reason = f"coverage target reached ({report.ratio:.0%})"
                break
            if stale >= self.patience:
                stop_reason = "diminishing returns — answers stopped adding detail"
                break

            gap = self.brain.rank_gaps(live, self.graph, self.ontology)
            self.channel.say(
                f"coverage {report.ratio:.0%} · {len(live)} open threads")
            question = self.brain.compose_question(gap, self.graph, history)
            answer = self.channel.ask(question)
            history.append((question, answer))

            if not answer.strip():
                exhausted.add(gap.key())
                stale += 1
                continue

            delta = self.brain.extract(answer, gap, self.graph, self.ontology)
            applied = self.graph.apply(delta, self.interviewee, self.session_id)
            if applied == 0:
                exhausted.add(gap.key())  # this thread isn't bearing fruit
                stale += 1
            else:
                stale = 0

        return InterviewResult(
            graph=self.graph, history=history, coverage_trace=trace,
            stop_reason=stop_reason, contradictions=self.graph.contradictions())
