from agentic_discovery.brain import MockBrain
from agentic_discovery.channels import ScriptedChannel
from agentic_discovery.engine import DiscoveryEngine
from agentic_discovery.modules import get
from agentic_discovery.report import build_html_report, ReportMeta


def _finished_process_run():
    module = get("process")
    engine = DiscoveryEngine(
        ontology=module.ontology,
        brain=MockBrain(scripted=list(module.demo.deltas)),
        channel=ScriptedChannel(answers=list(module.demo.answers), echo=False),
        interviewee="tester")
    return module, engine.run()


def test_report_is_self_contained_and_grounded():
    module, result = _finished_process_run()
    artifacts = module.synthesize(result.graph)
    html = build_html_report(
        result.graph, artifacts,
        ReportMeta(module_title=module.title,
                   goal=module.ontology.description,
                   coverage_trace=result.coverage_trace,
                   stop_reason=result.stop_reason,
                   history=result.history))
    # No template placeholders left behind.
    assert "__DATA__" not in html and "__TITLE__" not in html
    # The diagram and a grounded finding survive into the page.
    assert "flowchart TD" in html
    assert "Manual data entry from PDF" in html
    # Rendering libraries are referenced (graphical output, not just text).
    assert "mermaid" in html and "vis-network" in html
    # Graph data is embedded for the interactive view.
    assert "Receive invoice" in html
