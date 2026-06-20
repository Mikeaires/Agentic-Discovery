# The walking skeleton (v0.1)

A runnable vertical slice of the discovery loop. The engine is use-case-agnostic;
process discovery is the first fully-built module.

## Run it

```bash
# Offline demo — deterministic mock brain replays a canned interview.
# No model, no network, no install. Watch the graph fill to 100% coverage.
python -m agentic_discovery --module process

python -m agentic_discovery --list           # the three modules
python -m agentic_discovery --module process --out ./out   # write artifacts

# Live interview with a real Claude interviewer (you answer by typing):
pip install -e '.[claude]'
python -m agentic_discovery --module process --claude

# Tests (pure logic: graph, coverage, the loop) — no model needed:
pip install -e '.[dev]' && pytest -q
```

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
| Pluggable use cases | `modules/` — `process` (full), `ai-usecases`, `architecture` (stubs) |

## The two seams that make it scale

1. **Discovery modules.** Adding a use case = adding an `Ontology` + synthesizers
   (+ optional demo). The engine, graph, brain, and channels never change. The
   two stub modules exist to prove this: they run on the identical loop.
2. **Interaction channels.** The engine only calls `ask()` / `say()`. Text is
   built; `VoiceChannel` documents the two voice paths (browser Web Speech API,
   or server-side STT/TTS) behind the same interface.

## Deliberately deferred (next steps)

- **Voice surface** — the lightest path is a thin web UI using the browser Web
  Speech API (STT + TTS) over a small API around `DiscoveryEngine`. Avatar later.
- **Richer ClaudeBrain** — LLM-driven contradiction narration; smarter gap
  ranking; tone passes on the question generator.
- **Multi-interviewee merge + maturity scoring** — the same engine, merging
  graphs across sessions and scoring per ontology layer (the architecture module).
- **Graph store** — JSON today; a typed store only when multi-session querying
  earns it.
