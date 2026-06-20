from agentic_discovery.brain import MockBrain
from agentic_discovery.channels import ScriptedChannel
from agentic_discovery.engine import DiscoveryEngine
from agentic_discovery.modules import get


def _run_process_demo():
    module = get("process")
    engine = DiscoveryEngine(
        ontology=module.ontology,
        brain=MockBrain(scripted=list(module.demo.deltas)),
        channel=ScriptedChannel(answers=list(module.demo.answers), echo=False),
        interviewee="tester",
    )
    return module, engine.run()


def test_demo_reaches_coverage_and_stops_cleanly():
    _, result = _run_process_demo()
    assert result.coverage_trace[-1] >= 0.85
    # Stops on its own once the graph is sufficiently/fully covered.
    assert any(k in result.stop_reason for k in ("coverage", "complete"))
    assert len(result.graph.nodes_of_type("Step")) == 4


def test_synthesizers_produce_grounded_artifacts():
    module, result = _run_process_demo()
    artifacts = module.synthesize(result.graph)
    assert "flowchart TD" in artifacts["process-map.mmd"]
    assert artifacts["process-map.mmd"].count("-->") == 3  # 4 steps, 3 links
    # The named pain point should drive a grounded use-case idea.
    assert "Manual data entry from PDF" in artifacts["ai-use-cases.md"]


def test_coverage_is_monotonic_nondecreasing():
    _, result = _run_process_demo()
    trace = result.coverage_trace
    assert all(b >= a for a, b in zip(trace, trace[1:]))
