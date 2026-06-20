from agentic_discovery.graph import (
    KnowledgeGraph, GraphDelta, NodeAssertion, EdgeAssertion, Claim,
)


def test_apply_delta_creates_nodes_and_edges():
    g = KnowledgeGraph()
    delta = GraphDelta(
        nodes=[NodeAssertion("Step", "Approve invoice")],
        edges=[EdgeAssertion("performs", "Actor", "Manager", "Step", "Approve invoice")])
    applied = g.apply(delta, source="alice", session_id="s1")
    assert applied == 2
    assert g.find("Step", "Approve invoice") is not None
    assert g.find("Actor", "Manager") is not None  # edge endpoint auto-created
    assert len(g.edges_to(g.node_id("Step", "Approve invoice"), "performs")) == 1


def test_provenance_and_confidence():
    g = KnowledgeGraph()
    g.upsert_node("Step", "X", Claim("alice", "s1", "exists", confidence=0.5))
    g.upsert_node("Step", "X", Claim("bob", "s1", "exists", confidence=0.9))
    node = g.find("Step", "X")
    assert node.sources == {"alice", "bob"}
    assert node.confidence == 0.9


def test_contradiction_detection():
    g = KnowledgeGraph()
    g.upsert_node("Step", "X", Claim("alice", "s1", "exists"),
                  attributes={"owner": "AP"})
    # A second source asserts a different value for the same attribute.
    g.upsert_node("Step", "X", Claim("bob", "s1", "owner=Finance"))
    conflicts = g.contradictions()
    assert any(attr == "owner" and set(vals) == {"AP", "Finance"}
               for _, attr, vals in conflicts)


def test_save_load_roundtrip(tmp_path):
    g = KnowledgeGraph()
    g.apply(GraphDelta(nodes=[NodeAssertion("Step", "A")]), "alice", "s1")
    path = tmp_path / "g.json"
    g.save(str(path))
    import json
    g2 = KnowledgeGraph.from_dict(json.load(open(path)))
    assert g2.find("Step", "A") is not None
