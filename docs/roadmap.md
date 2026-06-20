# Roadmap

A staged path from idea to something testable, ordered so each stage de-risks the next.

## Stage 0 — Concept (done)
Framework, why-knowledge-graph, the loop, the two-layer ontology, first use case.
Captured in `README.md` and `docs/architecture.md`.

## Stage 1 — Walking skeleton of the loop (the real first build)
Goal: prove the *adaptive, graph-driven* loop end-to-end on one process, in text.

- Hand-author a small **process-discovery backbone ontology** (~8 entity types, ~6 relations,
  ~5 coverage rules).
- Implement the graph as an in-memory property graph persisted to JSON, with `Claim`-level
  provenance.
- Implement the four LLM roles as separate prompts over a shared graph: **planner**,
  **question generator**, **extractor**, **critic**.
- Run as a turn-based CLI chat. One question per turn; show a live **coverage meter** so you
  can watch the graph fill.
- Stop on coverage threshold or diminishing returns.

**Success test:** interview yourself about a process you know well. Does it ask sensible,
non-repetitive questions, notice when it has a gap, and stop at the right time?

## Stage 2 — Outputs that prove value
- Synthesizer: render the graph to a **Mermaid process map** + a **markdown process doc** with
  provenance links.
- **Pain-point register → AI use-case ideas**, each grounded in a specific friction in the map.

**Success test:** is the generated map something you'd actually show a client? Are the
use-case ideas concrete and traceable rather than generic?

## Stage 3 — Robustness on real, messy input
- Contradiction handling and triangulation (re-ask low-confidence / conflicting claims).
- Emergent-node handling polished (extension layer attaches cleanly without breaking outputs).
- Tone/UX pass on the question generator (warmth, role-adaptation, letting people digress).

**Success test:** interview a colleague about a process *you* don't know. Does the agent —
not you — drive the discovery to a usable result?

## Stage 4 — Multi-interviewee + the maturity assessment vertical
- Merge multiple sessions into one graph; surface cross-source disagreement as findings.
- New **maturity-model ontology** (platform layers) + per-layer **scorecard** synthesizer.
- This is the same engine, new ontology + multiple sources — which is why it comes after the
  process slice is solid.

## Stage 5 — Surface & scale (partly built in v0.2)
- **Web UI (built)** — mobile-first chat over the unchanged engine (`web/`,
  `WebChannel`), with a live coverage meter.
- **Voice (built, lightweight)** — browser Web Speech API for speech-to-text and
  text-to-speech, behind the same channel. Server-side STT/TTS and an avatar are
  the next increments on this same seam.
- **Graphical report (built)** — `report.py` renders the graph to a self-contained
  HTML page (diagram + interactive graph + findings + provenance).
- Still ahead: a one-command public URL for phone access; persistent typed graph
  store if multi-session querying demands it.

## Things to deliberately *not* do early
- Don't build a fancy graph database before the loop works (JSON/SQLite is fine).
- Don't try voice before text is good.
- Don't start with the open-ended "find AI use cases from scratch" goal — fuzziest stopping
  condition, worst first target.
- Don't collapse the LLM roles into one mega-prompt — you lose the ability to improve and
  evaluate planner vs extractor vs critic independently.
