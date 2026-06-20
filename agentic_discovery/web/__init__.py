"""Web surface — run a discovery interview from a browser (incl. a phone).

A thin HTTP layer around the unchanged `DiscoveryEngine`. The engine runs in a
background thread and talks through a queue-backed `WebChannel`; each HTTP turn
delivers one answer and pulls the next question. The same engine, graph, brain,
and ontology drive it — the browser is just another interaction channel, and
the rendered HTML report is the graphical deliverable.
"""

from .server import serve, WebChannel, SessionManager  # noqa: F401
