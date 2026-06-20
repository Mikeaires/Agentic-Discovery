"""The web session driver, exercised without sockets or a model.

Drives SessionManager directly in demo mode: the engine runs in its thread and
communicates through the queue-backed WebChannel, exactly as over HTTP.
"""

from agentic_discovery.web import SessionManager


def test_demo_session_runs_to_completion_over_the_channel():
    mgr = SessionManager()
    sess, first = mgr.create("process", mode="demo", interviewee="tester")

    assert first["kind"] == "question"
    assert first["session_id"] == sess.id

    d = first
    turns = 0
    while d["kind"] == "question" and turns < 15:
        d = sess.submit("(an answer)")
        turns += 1

    assert d["kind"] == "done"
    assert d["coverage"] >= 0.85
    assert d["nodes"] == 14
    assert d["report_url"].endswith("/report")

    # The deliverable renders and is grounded in what was captured.
    html = sess.report_html()
    assert "flowchart TD" in html
    assert "Manual data entry from PDF" in html


def test_report_before_finish_is_graceful():
    mgr = SessionManager()
    sess, _ = mgr.create("process", mode="demo", interviewee="t")
    # First question is pending; result not set yet.
    assert "not finished" in sess.report_html().lower()
