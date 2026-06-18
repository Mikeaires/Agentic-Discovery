# Architecture notes

This document goes one level deeper than the README on the components, the data model, and
the decisions that shape a prototype.

## Components and their contracts

Think of each as a separately-promptable role (in Claude Agent SDK terms, these can be
sub-agents or just distinct tool-using prompts sharing the graph as state).

### 1. Target ontology (config, not code at runtime)
Defines, per discovery type:
- **Entity types** and their attributes (e.g. `Step{name, duration, frequency}`).
- **Relation types** (e.g. `Step -follows-> Step`, `Actor -performs-> Step`,
  `Step -reads/writes-> DataObject`, `Step -uses-> System`).
- **Coverage rules** = the "definition of done". Predicates over the graph, e.g.
  *"every Step has ≥1 Actor and ≥1 input and ≥1 output"*, *"no Handoff has a null receiver"*.
- **Salience hints** = which gaps tend to matter most (priors for the planner).

### 2. Planner — "what should we learn next?"
Input: current graph + target ontology (as *typed gaps*, not transcript).
Output: a single next **objective** (e.g. *"clarify what triggers Step 'Approve invoice' and
who can reject it"*), plus a priority and rationale.
Heuristic for gap value: `severity (is it required by coverage rules?) × centrality (how many
other unknowns does it unlock?) × uncertainty (confidence gap) × novelty (avoid re-asking)`.
Start with an LLM ranking the gap list; formalize the scoring only if needed.

### 3. Question generator — objective → human question
Input: objective + recent conversation + interviewee profile (role, seniority).
Output: a warm, natural question + optional follow-up probes. Adapts vocabulary to the
person's role. Explicitly allowed to let the person digress when it's productive.

### 4. Extractor — answer → graph delta
Input: the answer (text) + current graph (for reconciliation).
Output: candidate nodes/edges/attributes, each with `{value, confidence, source, timestamp,
verbatim_quote}`. Responsibilities: entity resolution (is this the same "approval step" they
mentioned earlier?), dedupe, and flagging *new* types not in the backbone (→ extension layer).

### 5. Critic — coverage, contradictions, stop/redirect
Input: graph + target ontology.
Output: coverage report, list of contradictions (same slot, different sources/values), and a
decision: continue / redirect to a different region / wrap up. Owns the **stopping rule**:
coverage threshold met **or** last N questions added little (diminishing returns).

### 6. Synthesizer — graph → deliverables
On demand. Renders:
- **Process map** as a Mermaid diagram (nodes = steps, edges = flow/handoffs).
- **Narrative process documentation** (markdown), each statement linkable to provenance.
- **Pain-point register** → **AI use-case ideas**, each grounded in a specific friction.
- For maturity work: a **scorecard** per ontology layer with evidence.

## Data model (start simple)

A property graph with provenance on every element:

```
Node  { id, type, label, attributes{...},
        confidence: 0..1,
        sources: [ {interviewee_id, session_id, timestamp, quote} ] }

Edge  { id, type, from, to, attributes{...},
        confidence, sources: [...] }

Claim { the unit of provenance — a single (source → assertion) pair.
        Multiple claims can support or contradict one node/edge. }
```

Keeping `Claim` separate from `Node`/`Edge` is what lets two interviewees disagree about the
same node without one overwriting the other — the node holds *both* claims and the critic
flags the conflict.

**Storage:** don't over-invest early. In-memory graph (e.g. NetworkX) persisted to JSON, or
SQLite, is enough to prove the loop. Graduate to a typed graph store (Neo4j / a triple store)
only when multi-session merging and querying justify it. The loop logic shouldn't care which.

## Key decisions (with a recommended default)

| Decision | Options | Recommended default | Why |
|---|---|---|---|
| Ontology style | backbone-only / emergent-only / **hybrid** | **hybrid** | grounded *and* adaptive |
| Interview mode | live turn-based chat / async questionnaire | **live turn-based chat** | simplest real adaptivity; one turn = one adapt |
| Agent stance | passive listener / **probing** | **probing** | expert value is in challenging vague/inconsistent answers |
| Modality | **text** / voice | **text first** | voice/transcription is an add-on, not the hard part |
| Graph store | JSON / SQLite / graph DB | **JSON or SQLite first** | prove the loop before infra |
| LLM roles | one prompt / **separate roles** | **separate roles** | planner vs extractor vs critic have different jobs; easier to evaluate and improve in isolation |

## How "dynamic but grounded" actually works, step by step

A concrete trace for process discovery:

1. Backbone says a process needs Steps, each with Actor/Input/Output/System. Graph is empty →
   every slot is a gap.
2. Planner picks the broadest opening gap → "walk me through the process at a high level."
3. Person describes 5 steps loosely. Extractor creates 5 Step nodes (low confidence, lots of
   empty slots) and an emergent node "compliance review" that wasn't in the backbone →
   attached via the extension layer.
4. Critic: coverage ~20%, biggest holes are missing Actors/Systems on each step, plus the
   emergent compliance node is unexplained.
5. Planner now targets the highest-value hole (say the compliance step, because it's central
   and unknown). Question generator asks specifically about it.
6. Loop continues, each answer filling/correcting slots, until coverage rules pass and new
   answers stop adding nodes → critic calls it. Synthesizer renders the map + doc + ideas.

The interview *felt* like a natural conversation; underneath, every turn was the graph telling
the planner where its biggest hole was.

## Provider / build note

This multi-role agentic loop is a natural fit for the **Claude Agent SDK** (tool use +
sub-agents) with the latest Claude models. The planner/extractor/critic can be distinct
tool-using prompts over a shared graph tool. We can go deeper on exact SDK wiring, model
choice, and prompt-caching strategy when we start the prototype.
