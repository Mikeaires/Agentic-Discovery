from agentic_discovery.graph import (
    KnowledgeGraph, GraphDelta, NodeAssertion, EdgeAssertion,
)
from agentic_discovery.ontology import compute_coverage
from agentic_discovery.modules.process_discovery import ONTOLOGY


def test_empty_graph_yields_anchor_gap():
    report = compute_coverage(KnowledgeGraph(), ONTOLOGY)
    assert report.ratio == 0.0
    assert len(report.gaps) == 1
    assert report.gaps[0].kind == "anchor"


def test_requirements_become_gaps_then_close():
    g = KnowledgeGraph()
    g.apply(GraphDelta(nodes=[NodeAssertion("Step", "Record")]), "a", "s1")
    report = compute_coverage(g, ONTOLOGY)
    # One Step, three required relations, none satisfied yet.
    assert report.total == 3
    assert report.satisfied == 0
    kinds = {gap.relation for gap in report.gaps if gap.kind == "relation"}
    assert {"performs", "uses", "writes"} <= kinds

    g.apply(GraphDelta(edges=[
        EdgeAssertion("performs", "Actor", "Maria", "Step", "Record"),
        EdgeAssertion("uses", "Step", "Record", "System", "SAP"),
        EdgeAssertion("writes", "Step", "Record", "DataObject", "Record in SAP"),
    ]), "a", "s1")
    report = compute_coverage(g, ONTOLOGY)
    assert report.satisfied == 3
    assert report.ratio == 1.0
