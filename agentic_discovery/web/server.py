"""A dependency-free web server for running interviews from a browser/phone.

Design: the engine's `run()` loop is synchronous and blocks on
`channel.ask()`. To drive it over stateless HTTP turns without rewriting the
engine, each session runs `engine.run()` in its own thread and communicates
through a `WebChannel` backed by two thread-safe queues. An HTTP "answer"
request pushes the answer onto the inbox and drains the outbox up to the next
question (or completion). The engine is reused verbatim — the browser is just
another `InteractionChannel`.

Built on `http.server` (stdlib) so it runs anywhere with no install. Binds
0.0.0.0 so it is reachable from a phone on the same network or via a tunnel /
forwarded port from this container.
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..channels import InteractionChannel
from ..engine import DiscoveryEngine, InterviewResult
from ..brain import ClaudeBrain, MockBrain
from ..modules import REGISTRY, get
from ..report import ReportMeta, build_html_report

_HERE = os.path.dirname(__file__)


# --------------------------------------------------------------------------- #
# Queue-backed channel: the bridge between blocking engine and HTTP turns.     #
# --------------------------------------------------------------------------- #
class WebChannel(InteractionChannel):
    def __init__(self) -> None:
        self.outbox: "queue.Queue[dict]" = queue.Queue()
        self.inbox: "queue.Queue[str]" = queue.Queue()

    def ask(self, question: str) -> str:
        self.outbox.put({"type": "question", "text": question})
        return self.inbox.get()  # blocks the engine thread until an answer

    def say(self, message: str) -> None:
        self.outbox.put({"type": "status", "text": message})


class Session:
    def __init__(self, module_name: str, mode: str, interviewee: str) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.module = get(module_name)
        self.mode = mode
        self.interviewee = interviewee or "web-user"
        self.channel = WebChannel()
        self.result: InterviewResult | None = None
        self.error: str | None = None
        self.created = time.time()

        if mode == "live":
            brain = ClaudeBrain()
        else:
            brain = MockBrain(scripted=list(
                self.module.demo.deltas if self.module.demo else []))
        self.engine = DiscoveryEngine(
            ontology=self.module.ontology, brain=brain, channel=self.channel,
            interviewee=self.interviewee)
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> dict:
        self._thread.start()
        return self._drain()

    def submit(self, answer: str) -> dict:
        if self.result is not None or self.error is not None:
            return self._final_payload()
        self.channel.inbox.put(answer)
        return self._drain()

    def _run(self) -> None:
        try:
            self.result = self.engine.run()
            self.channel.outbox.put({"type": "done"})
        except Exception as exc:  # surface model/network failures to the client
            self.error = f"{type(exc).__name__}: {exc}"
            self.channel.outbox.put({"type": "error", "text": self.error})

    def _drain(self, timeout: float = 180.0) -> dict:
        """Pull outbox until the next question / done / error; fold in status."""
        status = None
        while True:
            try:
                msg = self.channel.outbox.get(timeout=timeout)
            except queue.Empty:
                return {"kind": "error", "text": "timed out waiting for the agent"}
            if msg["type"] == "status":
                status = msg["text"]
                continue
            if msg["type"] == "question":
                return {"kind": "question", "text": msg["text"],
                        "status": status, "coverage": self._coverage()}
            if msg["type"] == "done":
                return self._final_payload()
            if msg["type"] == "error":
                return {"kind": "error", "text": msg["text"]}

    def _coverage(self) -> float:
        from ..ontology import compute_coverage
        return round(compute_coverage(self.engine.graph, self.module.ontology).ratio, 3)

    def _final_payload(self) -> dict:
        if self.error:
            return {"kind": "error", "text": self.error}
        r = self.result
        return {
            "kind": "done",
            "stop_reason": r.stop_reason if r else "",
            "coverage": (r.coverage_trace[-1] if r and r.coverage_trace else 0),
            "coverage_trace": r.coverage_trace if r else [],
            "nodes": len(r.graph.nodes) if r else 0,
            "edges": len(r.graph.edges) if r else 0,
            "contradictions": len(r.contradictions) if r else 0,
            "report_url": f"/api/session/{self.id}/report",
            "graph_url": f"/api/session/{self.id}/graph.json",
        }

    # -- deliverables ---------------------------------------------------------
    def report_html(self) -> str:
        if self.result is None:
            return "<h1>Interview not finished yet.</h1>"
        artifacts = self.module.synthesize(self.result.graph)
        meta = ReportMeta(
            module_title=self.module.title, goal=self.module.ontology.description,
            interviewee=self.interviewee,
            coverage_trace=self.result.coverage_trace,
            stop_reason=self.result.stop_reason, history=self.result.history)
        return build_html_report(self.result.graph, artifacts, meta)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, module_name: str, mode: str, interviewee: str) -> tuple[Session, dict]:
        sess = Session(module_name, mode, interviewee)
        with self._lock:
            self._sessions[sess.id] = sess
        first = sess.start()
        first["session_id"] = sess.id
        return sess, first

    def get(self, sid: str) -> Session | None:
        with self._lock:
            return self._sessions.get(sid)


# --------------------------------------------------------------------------- #
# HTTP routing                                                                 #
# --------------------------------------------------------------------------- #
def _live_available() -> bool:
    try:
        import anthropic  # noqa: F401
        return True
    except Exception:
        return False


class Handler(BaseHTTPRequestHandler):
    manager: SessionManager = None  # set on the server instance
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # quieter console
        pass

    # -- helpers --------------------------------------------------------------
    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def _read_body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    # -- routes ---------------------------------------------------------------
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            with open(os.path.join(_HERE, "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if path == "/api/modules":
            live = _live_available()
            return self._json({
                "live_available": live,
                "modules": [
                    {"name": m.name, "title": m.title,
                     "has_demo": m.demo is not None}
                    for m in REGISTRY.values()],
            })
        if path.startswith("/api/session/") and path.endswith("/report"):
            sid = path.split("/")[3]
            sess = self.manager.get(sid)
            if not sess:
                return self._send(404, b"unknown session", "text/plain")
            return self._send(200, sess.report_html().encode(),
                              "text/html; charset=utf-8")
        if path.startswith("/api/session/") and path.endswith("/graph.json"):
            sid = path.split("/")[3]
            sess = self.manager.get(sid)
            if not sess or sess.result is None:
                return self._send(404, b"no graph", "text/plain")
            return self._json(sess.result.graph.to_dict())
        return self._send(404, b"not found", "text/plain")

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/session":
            body = self._read_body()
            mode = body.get("mode", "demo")
            module_name = body.get("module", "process")
            if mode == "live" and not _live_available():
                return self._json(
                    {"kind": "error",
                     "text": "live mode needs the anthropic SDK installed"}, 400)
            try:
                _, payload = self.manager.create(
                    module_name, mode, body.get("interviewee", "web-user"))
            except KeyError as e:
                return self._json({"kind": "error", "text": str(e)}, 400)
            return self._json(payload)

        if path.startswith("/api/session/") and path.endswith("/answer"):
            sid = path.split("/")[3]
            sess = self.manager.get(sid)
            if not sess:
                return self._json({"kind": "error", "text": "unknown session"}, 404)
            answer = self._read_body().get("answer", "")
            return self._json(sess.submit(answer))

        return self._send(404, b"not found", "text/plain")


def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    manager = SessionManager()
    handler = type("BoundHandler", (Handler,), {"manager": manager})
    httpd = ThreadingHTTPServer((host, port), handler)
    shown = host if host != "0.0.0.0" else "localhost"
    print(f"\n  Agentic Discovery — web interview")
    print(f"  open  http://{shown}:{port}/  on this machine,")
    print(f"  or forward / tunnel port {port} to reach it from your phone.")
    print(f"  live mode available: {_live_available()}  (demo always works)\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  bye.")
        httpd.shutdown()
