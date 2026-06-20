# The walking skeleton (v0.2)

A runnable vertical slice of the discovery loop. The engine is use-case-agnostic;
process discovery is the first fully-built module. v0.2 adds a phone-friendly web
interview (with optional voice) and a graphical HTML report.

## Run it

```bash
# Offline demo — deterministic mock brain replays a canned interview.
# No model, no network, no install. Watch the graph fill to 100% coverage.
python -m agentic_discovery --module process

python -m agentic_discovery --list           # the three modules
python -m agentic_discovery --module process --out ./out   # write artifacts + report.html

# Live interview with a real Claude interviewer (you answer by typing):
pip install -e '.[claude]'
python -m agentic_discovery --module process --claude

# Tests (pure logic: graph, coverage, the loop, report, web driver) — no model:
pip install -e '.[dev]' && pytest -q
```

## Use it from a phone

```bash
python -m agentic_discovery --serve            # binds 0.0.0.0:8000
```

Open the printed URL in a browser. Because this runs in an ephemeral container,
reach it from a phone by forwarding / tunnelling port 8000 (e.g. an SSH tunnel,
the platform's port-forwarding, or a tunnel service) and opening that URL on the
phone. The UI is a mobile-first chat:

- **Voice in/out** via the browser Web Speech API — tap 🎙 to dictate an answer,
  toggle 🔊 to have questions read aloud. No vendor keys; this is the lightweight
  voice surface the roadmap called for (avatar later).
- **Demo mode** works fully offline. **Live mode** uses Claude and needs the
  anthropic SDK plus `ANTHROPIC_API_KEY` (auth errors surface back into the chat).
- At the end you get a **graphical report** (`/api/session/<id>/report`): a
  rendered process diagram, an interactive knowledge graph, the written findings
  and AI use-case ideas, plus coverage, provenance and contradictions.

The web layer is just another `InteractionChannel` (`WebChannel`, queue-backed)
around the *unchanged* engine running in a background thread — one HTTP turn per
question/answer. See `agentic_discovery/web/`.

## How the pieces map to the concept

| Concept (README) | Code |
|---|---|
| Knowledge graph (provenance + confidence) | `graph.py` — `KnowledgeGraph`, `Claim`, `Node`, `Edge` |
| Target ontology + coverage / gaps | `ontology.py` — `Ontology`, `compute_coverage` |
| Planner / question-gen / extractor (the model roles) | `brain.py` — `Brain`, `MockBrain`, `ClaudeBrain` |
| Critic (coverage, contradictions, stopping) | `engine.py` + `KnowledgeGraph.contradictions()` |
| The discovery loop | `engine.py` — `DiscoveryEngine.run()` |
| Interaction channels (text now, voice/avatar later) | `channels.py` — `TextChannel`, `VoiceChannel` (scaffold) |
| Synthesizers (graph → deliverables) | `modules/process_discovery.py` — Mermaid map, doc, use-cases |
| Graphical/HTML deliverable | `report.py` — `build_html_report` (diagram + interactive graph + findings) |
| Phone/web surface | `web/` — `WebChannel`, `SessionManager`, stdlib server, mobile UI + voice |
| Pluggable use cases | `modules/` — `process` (full), `ai-usecases`, `architecture` (stubs) |

## The two seams that make it scale

1. **Discovery modules.** Adding a use case = adding an `Ontology` + synthesizers
   (+ optional demo). The engine, graph, brain, and channels never change. The
   two stub modules exist to prove this: they run on the identical loop.
2. **Interaction channels.** The engine only calls `ask()` / `say()`. Text is
   built; `VoiceChannel` documents the two voice paths (browser Web Speech API,
   or server-side STT/TTS) behind the same interface.

## Deliberately deferred (next steps)

- **Avatar** — the web/voice surface is built (browser Web Speech API over the
  `WebChannel`); a talking avatar plugs into the same channel next.
- **Hosting/tunnel** — `--serve` binds `0.0.0.0`; a one-command public URL
  (tunnel or deploy) would remove the manual port-forward step for phone use.
- **Richer ClaudeBrain** — LLM-driven contradiction narration; smarter gap
  ranking; tone passes on the question generator.
- **Multi-interviewee merge + maturity scoring** — the same engine, merging
  graphs across sessions and scoring per ontology layer (the architecture module).
- **Graph store** — JSON today; a typed store only when multi-session querying
  earns it.
