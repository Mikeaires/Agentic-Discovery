"""Module #1: business-process discovery + AI redesign ideation.

Generic over any process (nothing domain-specific is hardcoded). The agent
discovers the specific process at runtime; the graph it builds *is* the process
map, and every pain point / manual step in it becomes a grounded AI use-case.
"""

from __future__ import annotations

from ..graph import GraphDelta, KnowledgeGraph, NodeAssertion, EdgeAssertion
from ..ontology import (
    EntityType, Ontology, RelationType, RequiredRelation,
)

ONTOLOGY = Ontology(
    name="business process",
    description="How a process actually works, end to end.",
    anchor_type="Step",
    entity_types=[
        EntityType("Step", "A unit of work in the process"),
        EntityType("Actor", "A person, team, or role that does work"),
        EntityType("System", "An application or tool used"),
        EntityType("DataObject", "An input consumed or output produced"),
        EntityType("Decision", "A branch point"),
        EntityType("PainPoint", "Friction, delay, error, or manual toil"),
        EntityType("Rule", "A policy or constraint governing a step"),
        EntityType("Metric", "How the step or process is measured"),
    ],
    relation_types=[
        RelationType("follows", ["Step"], ["Step"], "ordering of steps"),
        RelationType("performs", ["Actor"], ["Step"], "who does the step"),
        RelationType("uses", ["Step"], ["System"], "system that supports the step"),
        RelationType("reads", ["Step"], ["DataObject"], "input consumed"),
        RelationType("writes", ["Step"], ["DataObject"], "output produced"),
        RelationType("handoff", ["Step"], ["Actor"], "work passed to someone"),
        RelationType("has_pain", ["Step"], ["PainPoint"], "friction at this step"),
        RelationType("governed_by", ["Step"], ["Rule"], "rule constraining the step"),
        RelationType("branches_to", ["Decision"], ["Step"], "outcome of a decision"),
        RelationType("measured_by", ["Step"], ["Metric"], "metric on the step"),
    ],
    required_relations=[
        RequiredRelation("Step", "performs", "in", 1,
                         "who performs this step?", severity=1.5),
        RequiredRelation("Step", "uses", "out", 1,
                         "which system(s) support this step?", severity=1.0),
        RequiredRelation("Step", "writes", "out", 1,
                         "what does this step produce (its output)?", severity=1.0),
    ],
    opening_objective=(
        "Walk me through this process at a high level, from the trigger to the "
        "outcome — what are the main steps, in order?"),
)


# --------------------------------------------------------------------------- #
# Synthesizers: graph -> deliverables                                          #
# --------------------------------------------------------------------------- #
def _ordered_steps(graph: KnowledgeGraph):
    steps = graph.nodes_of_type("Step")
    has_incoming = {e.target for e in graph.edges.values() if e.type == "follows"}
    starts = [s for s in steps if s.id not in has_incoming] or steps[:1]
    order, seen = [], set()
    frontier = list(starts)
    while frontier:
        node = frontier.pop(0)
        if node.id in seen:
            continue
        seen.add(node.id)
        order.append(node)
        for e in graph.edges_from(node.id, "follows"):
            if e.target in graph.nodes:
                frontier.append(graph.nodes[e.target])
    for s in steps:  # append any not reachable via follows
        if s.id not in seen:
            order.append(s)
    return order


def _actor_of(graph: KnowledgeGraph, step):
    for e in graph.edges_to(step.id, "performs"):
        return graph.nodes[e.source].label
    return None


def _labels(graph: KnowledgeGraph, step, rel: str):
    return [graph.nodes[e.target].label for e in graph.edges_from(step.id, rel)
            if e.target in graph.nodes]


def mermaid_map(graph: KnowledgeGraph) -> str:
    lines = ["flowchart TD"]
    pain_ids = set()
    for i, step in enumerate(_ordered_steps(graph)):
        actor = _actor_of(graph, step)
        systems = _labels(graph, step, "uses")
        sub = " · ".join(filter(None, [
            f"👤 {actor}" if actor else "",
            f"🖥 {'/'.join(systems)}" if systems else ""]))
        text = step.label + (f"<br/><small>{sub}</small>" if sub else "")
        nid = f"S{i}"
        step._mermaid = nid  # type: ignore[attr-defined]
        lines.append(f'    {nid}["{text}"]')
        if graph.edges_from(step.id, "has_pain"):
            pain_ids.add(nid)
    for step in _ordered_steps(graph):
        for e in graph.edges_from(step.id, "follows"):
            tgt = graph.nodes.get(e.target)
            if tgt is not None and hasattr(step, "_mermaid") and hasattr(tgt, "_mermaid"):
                lines.append(f"    {step._mermaid} --> {tgt._mermaid}")  # type: ignore[attr-defined]
    for nid in pain_ids:
        lines.append(f"    class {nid} pain;")
    lines.append("    classDef pain fill:#ffe3e3,stroke:#e03131;")
    return "\n".join(lines)


def process_doc(graph: KnowledgeGraph) -> str:
    out = ["# Process documentation\n"]
    for i, step in enumerate(_ordered_steps(graph), 1):
        out.append(f"## {i}. {step.label}")
        actor = _actor_of(graph, step)
        if actor:
            out.append(f"- **Performed by:** {actor}")
        for rel, label in [("uses", "Systems"), ("reads", "Inputs"),
                           ("writes", "Outputs"), ("governed_by", "Rules")]:
            vals = _labels(graph, step, rel)
            if vals:
                out.append(f"- **{label}:** {', '.join(vals)}")
        pains = _labels(graph, step, "has_pain")
        if pains:
            out.append(f"- **Pain points:** {', '.join(pains)}")
        handoffs = _labels(graph, step, "handoff")
        if handoffs:
            out.append(f"- **Hands off to:** {', '.join(handoffs)}")
        srcs = ", ".join(sorted(step.sources))
        out.append(f"- _source: {srcs} (confidence {step.confidence:.0%})_\n")
    return "\n".join(out)


def usecase_ideas(graph: KnowledgeGraph) -> str:
    out = ["# AI use-case ideas (grounded in the map)\n"]
    n = 0
    for step in _ordered_steps(graph):
        pains = _labels(graph, step, "has_pain")
        for pain in pains:
            n += 1
            out.append(
                f"## {n}. Address '{pain}' at step '{step.label}'\n"
                f"- **Grounding:** the team named this friction directly.\n"
                f"- **Candidate:** an AI assist that removes the toil behind "
                f"'{pain}' (e.g. extract/validate/auto-fill) so '{step.label}' "
                f"needs human attention only on exceptions.\n")
        # A manual-looking step (a human performer, no decision branch) is a
        # candidate even without a named pain.
        if not pains and _actor_of(graph, step) and not graph.edges_from(step.id, "uses"):
            n += 1
            out.append(
                f"## {n}. Automate / assist step '{step.label}'\n"
                f"- **Grounding:** performed by a person with no supporting "
                f"system — a likely manual bottleneck.\n"
                f"- **Candidate:** introduce tooling or an agent to handle the "
                f"routine path of '{step.label}'.\n")
    if n == 0:
        out.append("_No pain points or manual steps captured yet — keep interviewing._")
    return "\n".join(out)


def synthesize(graph: KnowledgeGraph) -> dict[str, str]:
    return {
        "process-map.mmd": mermaid_map(graph),
        "process-doc.md": process_doc(graph),
        "ai-use-cases.md": usecase_ideas(graph),
    }


# --------------------------------------------------------------------------- #
# Offline demo: aligned answers + extracted deltas (no model needed)          #
# --------------------------------------------------------------------------- #
def _step(label):
    return NodeAssertion("Step", label)


_DEMO = None


def _demo_script():
    from . import DemoScript

    answers = [
        ("Sure. It kicks off when a supplier invoice lands in our shared AP "
         "mailbox. From there AP records it in SAP, a cost-centre manager "
         "reviews and approves it, and finally the finance team schedules the "
         "payment run."),
        ("Maria, our AP clerk, handles receiving and recording. The cost-centre "
         "manager does the approval, and the finance team owns scheduling. "
         "Honestly recording is painful — it's manual data entry, retyping "
         "numbers off a PDF."),
        ("Everything after intake lives in SAP — recording, the approval "
         "workflow and the payment scheduling all happen there. The invoices "
         "themselves just arrive in the shared Outlook mailbox."),
        ("Each step produces something: intake gives us the raw invoice PDF, "
         "recording creates the invoice record in SAP, approval produces the "
         "signed-off decision, and scheduling creates the payment-run entry. "
         "After approval it hands off to finance."),
    ]
    steps = ["Receive invoice", "Record invoice", "Approve invoice",
             "Schedule payment"]
    deltas = [
        GraphDelta(
            nodes=[_step(s) for s in steps],
            edges=[EdgeAssertion("follows", "Step", a, "Step", b)
                   for a, b in zip(steps, steps[1:])]),
        GraphDelta(edges=[
            EdgeAssertion("performs", "Actor", "AP clerk (Maria)", "Step", "Receive invoice"),
            EdgeAssertion("performs", "Actor", "AP clerk (Maria)", "Step", "Record invoice"),
            EdgeAssertion("performs", "Actor", "Cost-centre manager", "Step", "Approve invoice"),
            EdgeAssertion("performs", "Actor", "Finance team", "Step", "Schedule payment"),
            EdgeAssertion("has_pain", "Step", "Record invoice", "PainPoint",
                          "Manual data entry from PDF")]),
        GraphDelta(edges=[
            EdgeAssertion("uses", "Step", "Receive invoice", "System", "Shared Outlook mailbox"),
            EdgeAssertion("uses", "Step", "Record invoice", "System", "SAP"),
            EdgeAssertion("uses", "Step", "Approve invoice", "System", "SAP"),
            EdgeAssertion("uses", "Step", "Schedule payment", "System", "SAP")]),
        GraphDelta(edges=[
            EdgeAssertion("writes", "Step", "Receive invoice", "DataObject", "Invoice (PDF)"),
            EdgeAssertion("writes", "Step", "Record invoice", "DataObject", "Invoice record in SAP"),
            EdgeAssertion("writes", "Step", "Approve invoice", "DataObject", "Approval decision"),
            EdgeAssertion("writes", "Step", "Schedule payment", "DataObject", "Payment-run entry"),
            EdgeAssertion("handoff", "Step", "Approve invoice", "Actor", "Finance team")]),
    ]
    return DemoScript(answers=[a for a in answers], deltas=deltas)


def _build_module():
    from . import DiscoveryModule
    return DiscoveryModule(
        name="process",
        title="Business-process discovery + AI redesign",
        ontology=ONTOLOGY,
        synthesize=synthesize,
        demo=_demo_script())


MODULE = _build_module()
