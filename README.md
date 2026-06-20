# Agentic Discovery

An agent that **interviews people to discover knowledge** — turning a fuzzy, high-level
goal ("understand how this process works", "assess the maturity of this company's data
platform", "find AI use cases for this team") into a *dynamic, personalized flow of
questions*, and capturing the answers as a **grounded, structured knowledge graph** that
becomes documentation, diagrams, assessments, and ideas.

> The hard, interesting part is not the questions — it's deciding *which question to ask
> next* given everything you already know, knowing *when you have enough*, and keeping the
> growing knowledge **grounded** so multiple noisy human answers turn into one coherent,
> traceable model of reality.

## The core thesis

A discovery interview is **goal-directed information acquisition**. You don't have a fixed
questionnaire; you have a *target* (the shape of knowledge you want to end up with) and you
greedily ask whatever question closes the biggest gap toward that target, adapting as each
answer reshapes what you still need to know.

This maps almost perfectly onto a knowledge graph:

- The **goal** is a *target ontology* — the entity types and relationships you need
  instantiated to consider the discovery "complete" (e.g. for a process: actors, steps,
  inputs, outputs, systems, decisions, handoffs, pain points, rules, metrics).
- The **current state** is the *partially-filled graph* — what you know so far, with
  confidence and provenance on every node and edge.
- **"What to ask next"** becomes a well-defined question over the graph: *find the
  highest-value missing or low-confidence or contradicted piece, and ask about that.*
- **"Am I done?"** becomes a *coverage metric* over the target subgraph plus a
  diminishing-returns check.

So the knowledge graph isn't decoration or a nice export at the end — it is the **control
structure that drives the interview** and the **memory that keeps it grounded**. That's the
bet of this project, and it's why the KG intuition is right.

## Why a knowledge graph (and not just "an LLM with the transcript")

A naive agent ("here's the whole conversation, ask the next question") demos well and then
falls apart on real interviews: it drifts, repeats itself, forgets to close gaps, can't tell
when it's done, and silently averages away contradictions. The graph fixes exactly these:

| Problem in naive approach | What the graph gives you |
|---|---|
| Doesn't know what's missing | Typed gaps: empty slots, dangling edges, unanswered decisions |
| Drifts / repeats questions | Planner sees explicit coverage, won't re-ask filled slots |
| Never knows when to stop | Coverage % over the target subgraph + diminishing returns |
| Loses the thread on long interviews | Compact structured state instead of an ever-growing transcript |
| Averages away disagreement | Every claim carries a source; contradictions are first-class signals |
| No traceability in outputs | Every fact links back to who said it, when, verbatim |

The contradictions point is worth emphasizing: when you interview *several* people, the most
valuable finding is often that **two teams describe the same process differently**. A graph
with per-source provenance surfaces that automatically; a blended transcript hides it.

## The discovery loop

Each interview runs a loop. State at the center is the knowledge graph.

```
        ┌──────────────────────────────────────────────┐
        │            TARGET ONTOLOGY (the goal)         │
        │  entity/relation types + "definition of done" │
        └───────────────────────┬──────────────────────┘
                                 │ defines gaps against
                                 ▼
   ┌─────────┐   gaps    ┌──────────────┐   objective   ┌──────────────┐
   │ CRITIC  │◀──────────│   PLANNER    │──────────────▶│  QUESTION    │
   │coverage,│           │ pick highest │               │  GENERATOR   │
   │contradi-│           │ value gap    │               │ phrase it    │
   │ctions,  │           └──────▲───────┘               │ warmly +     │
   │ when to │                  │                       │ follow-ups   │
   │  stop   │           updates│ graph                 └──────┬───────┘
   └────┬────┘                  │                              │ question
        │ continue/             │                              ▼
        │ redirect/      ┌──────┴───────┐   structured   ┌──────────────┐
        │ close          │  KNOWLEDGE   │◀───────────────│  EXTRACTOR   │
        └───────────────▶│    GRAPH     │  claims +      │ answer → nodes│
                         │  (+provenance│  provenance    │ /edges, recon-│
                         │  +confidence)│                │ cile, dedupe  │
                         └──────────────┘                └──────▲───────┘
                                                                │ answer
                                                          ( human reply )
```

1. **Target ontology** — what "knowing enough" means for this discovery type.
2. **Planner** — given the graph + goal, choose the next *objective* (the most valuable gap).
3. **Question generator** — turn the objective into a natural, context-aware question with
   probing follow-ups. Conversational, not a survey.
4. **Extractor** — parse the answer into candidate entities/relations/attributes, reconcile
   into the graph with provenance + confidence, detect new threads the answer opened.
5. **Critic** — assess coverage, flag contradictions, decide continue / redirect / close.
6. **Synthesizer** (at the end / on demand) — render the graph into deliverables.

## The key design idea: a two-layer ontology

The tension you feel — *"grounded thread of information that is still dynamic"* — is real,
and it's resolved with a **dual-layer schema**:

- **Backbone (fixed):** a small, hand-authored ontology per discovery type. Guarantees you
  never miss known-important dimensions and gives outputs a stable shape. This is the
  "grounded thread."
- **Extension (emergent):** the agent can attach new entity/relation types it discovers and
  the backbone didn't anticipate. This is the "dynamic and adaptable" part — the interview
  follows reality instead of railroading the person through a checklist.

Backbone keeps it rigorous; extension keeps it honest. Most failures of survey-style tools
come from having only the backbone; most failures of pure-LLM agents come from having only
the extension.

## What to build first (recommended vertical slice)

You listed three directions. I'd start with the **smallest one that exercises the whole
loop end-to-end**, then reuse the engine for the bigger ones.

**Recommended: single-process discovery + AI redesign ideation.**

Why this one first:

- **Bounded ontology.** A process has a known backbone (actors, steps, inputs, outputs,
  systems, decisions, handoffs, rules, pain points, metrics). Small enough to hand-author.
- **Unambiguous "done."** Coverage is checkable: every step has an actor + input + output +
  system, no handoff dangles, every decision has its branches. You can *see* completeness.
- **The KG value is visual and obvious.** The graph *is* the process map — render it as a
  diagram and the grounding is immediately legible.
- **Easy to test.** You can run it on yourself or one colleague about a process you know,
  and judge the output directly.
- **Extends straight into ideation.** Every pain point / manual step / handoff in the graph
  is a grounded candidate for an AI intervention — use-case ideation falls out of the same
  structure, each idea traceable to a real friction in the map.

The other two are *the same engine with a different ontology and more interviewees*:

- **Data/AI platform maturity assessment** = a maturity-model ontology (layers: ingestion,
  storage, governance, modeling, serving, MLOps, org/skills…) + multiple interviewees +
  scoring. Higher value, much bigger scope, multi-role triangulation, fuzzier evaluation.
- **Open-ended AI use-case discovery** = the fuzziest goal and the hardest "when am I done",
  so worst first target even though it's exciting.

Building the process slice first **de-risks** the maturity assessment, which is the
ambitious end-state.

## Honest risks and open decisions

- **The planner/critic is the differentiator and the risk.** Feed it *typed gaps*, not raw
  transcript. That's what makes "what next" reliable and makes stopping principled.
- **Extraction errors compound** in the graph. Keep confidence + provenance on everything and
  let the critic re-ask low-confidence claims (triangulation, not blind trust).
- **Tone matters.** A gap-driven agent can feel like an interrogation. The question generator
  needs warmth, context, and the judgment to let people ramble (rambling is where emergent
  nodes come from).
- **Humans are vague and contradictory.** Treat disagreement as signal, not noise.
- **Consent & privacy.** Interviewing real employees means recording/transcription consent,
  and being careful with what the graph stores about people.

Open decisions to make before/while building (see `docs/architecture.md`):
backbone-only vs hybrid ontology (→ hybrid), live turn-based chat vs async questionnaire
(→ live chat, simplest form of adaptive), how opinionated/probing the agent should be,
graph store (start simple), and text-first vs voice (→ text first).

## Status

**Walking skeleton built (v0.2).** A runnable, use-case-agnostic discovery engine with the
full loop (graph → planner → question → extractor → critic), three discovery modules
(process discovery fully built; AI-use-case and architecture discovery wired as stubs on the
same engine), and synthesizers that turn the graph into a Mermaid process map, a process doc,
and grounded AI use-case ideas. Runs offline with a deterministic mock brain, or live against
`claude-opus-4-8`.

On top of that, v0.2 adds the human-interaction surface:

- **Phone/web interview** — a mobile-first chat UI over the *unchanged* engine (the browser is
  just another interaction channel), with **voice in/out** via the browser Web Speech API.
- **Graphical HTML report** — a single self-contained page with a rendered process diagram, an
  interactive knowledge graph, the written findings, and coverage/provenance/contradiction panels.

```bash
python -m agentic_discovery --module process   # offline demo, no install needed
python -m agentic_discovery --serve            # phone-friendly web UI (+ voice)
python -m agentic_discovery --module process --out ./out   # writes report.html
```

See **`BUILD.md`** for how to run it and how the code maps to this concept, plus
`docs/architecture.md` and `docs/roadmap.md` for the design.
