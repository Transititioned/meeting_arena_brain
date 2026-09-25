# Meeting Arena — Canonical Semantic Architecture

This is the authoritative description of how behaviour is composed in
Meeting Arena Brain. It exists so behavioural-layer decisions don't drift
across sessions: read it before changing persona, stance, condition, move
selection, or prompt composition.

The layers below **must remain conceptually separate** in code, in config,
and in prompts. Collapsing them back together is the single most likely
regression in this codebase.

## 1. The layer model

```
SILLYTAVERN PERSONA          stable person + voice + examples
        +
POWER DIFFICULTY             explicit political difficulty of the scenario/room
        +
RELATIONSHIP / AUTHORITY     explicit formal authority: current actor → user
        +
STANCE                       explicit attitude toward the current proposal
        +
TEMPORARY CONDITION          explicit short-lived modifier
        +
DETERMINISTIC MOVE           Python-selected strategic action
        +
LIGHTWEIGHT CONTEXT          optional rendering variation only
        ↓
REMOTE LLM                   renders one believable response
```

**Power difficulty vs. relationship — do not conflate these:** power
difficulty is a *room-wide scenario property* (how politically difficult
this meeting is, for everyone in it). Relationship is *actor-to-user
metadata* (this specific actor's formal authority over the user,
independent of the room). In one multi-person meeting these can differ per
actor while power difficulty stays constant for the room:

```
Room power difficulty = AMBER
  Priya  relationship = BOSS
  Marcus relationship = PEER
  Dana   relationship = PEER
```

**Iteration-one note:** power difficulty is fully inert — defined and
plumbed (parsed, tracked, logged) but does **not** yet feed any remote LLM
or influence any other layer; see section 4. Relationship is likewise
permanently inert in *actor generation* (never reaches the actor-rendering
LLM call), but it now has exactly one downstream consumer: `BOSS`
deterministically activates the Managing Up repertoire for the explicit
Coach path (`POST /v1/coach`, section 8), which does make its own, separate
LLM call. That Coach path is now implemented as an MVP.

## 2. Ownership boundaries

| Concern | Owner | Where |
|---|---|---|
| Stable persona (who someone is, voice, cadence, normal challenge style, dialogue examples) | SillyTavern | The character card, not this repo |
| Power difficulty (political difficulty of the scenario/room) | This repo, scenario-level control metadata (iteration one: not yet consumed downstream) | `config/power/power.yaml` |
| Relationship / authority (current actor's formal authority over/under the user) | This repo, actor-to-user control metadata; permanently inert in actor generation. Its one downstream consumer is the Managing Up resolver (section 8), called by the Coach path (`POST /v1/coach`) | `config/relationships/relationships.yaml` |
| Stance (attitude toward the current proposal) | This repo, rendering overlay | `config/stances/stances.yaml` |
| Temporary condition (what kind of day/moment the actor is having) | This repo, rendering overlay | `config/conditions/conditions.yaml` |
| Move selection (the strategic conversational action) | This repo, deterministic Python | `arena_brain/engine.py::select_move` |
| Natural wording | The remote LLM | One call per actor response, one per explicit Coach request |
| Which remote model each lane uses | This repo, independent per lane (section 9) | `arena_brain/settings.py` (`ARENA_ACTOR_MODEL` / `ARENA_COACH_MODEL`) |

The actor ID (`priya` / `marcus` / `dana`) stays in the brain purely for
**routing**: which move guidance applies, which repeated-move history to
check, whose turn this is. It is not a vehicle for persona text. The brain
must not become a second persona engine — do not inject a behavioural
profile (authority, pace, warmth, etc.) into the prompt it builds. That
description belongs in the SillyTavern character card.

## 3. Closed vocabularies

Power difficulty, relationship, stance, and temporary condition are each a
small, closed, named vocabulary — never free text, never LLM-inferred. An
unrecognised or missing value degrades safely to no override.

**Power difficulty** (`config/power/power.yaml`) — how politically difficult
the scenario/room is, independent of any single actor's persona, stance, or
condition:

| Value | Meaning |
|---|---|
| `GREEN` | Normal organisational hierarchy. Bosses are still bosses and people protect their own responsibilities, but disagreement is mainly substantive rather than political |
| `AMBER` | Status behaviour is present — playing to the boss, seeking visibility, subtle positioning, offloading awkward work, letting someone else take political heat — but stays plausible, socially normal and deniable rather than overtly hostile |
| `RED` | A credible political threat is present — scope/authority encroachment, publicly distancing from a failure, undermining someone's standing, joining a pile-on, transferring accountability while keeping influence — while still reading as believable workplace politics, not cartoon villainy |

**Iteration-one rule:** `ARENA_POWER` is control metadata only. It is parsed,
tracked, and logged, but must not affect move selection, stance, condition,
repeated-move logic, or rendering, and must not inject any guidance into the
LLM prompt. Later tasks will decide how GREEN/AMBER/RED actually affect
simulation behaviour — do not pre-empt that here.

**Relationship / authority** (`config/relationships/relationships.yaml`) —
the current actor's formal authority relationship to the user. This is
**actor-to-user metadata, not a room-wide scenario property** (see the
worked example above) — do not conflate it with power difficulty:

| Value | Meaning |
|---|---|
| `BOSS` | The current actor has direct managerial/formal authority over the user. Deterministically activates the Managing Up coaching repertoire in the Coach path (section 8, `POST /v1/coach`) |
| `PEER` | The current actor has no direct managerial authority over the user, and the user has none over them. May still differ in seniority, influence, or political standing — do not assume equal footing |
| `DIRECT_REPORT` | The user has formal managerial authority over the current actor. Future activation point for leadership/delegation coaching — not implemented yet |

The initial vocabulary is deliberately small. A senior stakeholder who
isn't the user's boss stays `PEER` for now — power difficulty and future
political/event tags are where influence and political threat get
captured, not relationship. Extend this vocabulary later only if real
scenarios prove it too coarse.

**Iteration-one rule:** `ARENA_RELATIONSHIP` is control metadata only with
respect to actor generation. It is parsed, tracked, and logged, but must
not affect move selection, stance, condition, power difficulty,
repeated-move logic, or rendering, and must never inject any guidance into
the *actor's* LLM prompt (`build_behavior_instruction()`). `BOSS` does
deterministically activate the Managing Up coaching repertoire (section 8)
— but that only reaches the separate, explicit Coach path (`POST
/v1/coach`), never the actor-generation path.

**Stance** (`config/stances/stances.yaml`) — the actor's attitude toward the
current proposal/discussion, independent of their stable personality:

| Value | Meaning |
|---|---|
| `NEUTRAL` | Normal baseline posture toward the proposal |
| `COLLABORATIVE` | Lean toward finding a workable path and common ground |
| `SCEPTICAL` | Withhold agreement until the reasoning is convincing; probe assumptions, evidence and consequences; remain open to persuasion |
| `OPPOSITIONAL` | Actively resist the proposal; surface weaknesses, costs and alternatives while remaining credible and professional — this does **not** mean rude, irrational, or aggressive |

**Temporary condition** (`config/conditions/conditions.yaml`) — what sort of
day/moment the actor is having, independent of stance:

| Value | Meaning |
|---|---|
| `NORMAL` | Usual character baseline |
| `PRESSURED` | External/time pressure; less conversational space, more urgency |
| `FRAZZLED` | Lower patience/composure; less social cushioning; mild irritation may show |
| `DEFENSIVE` | More sensitive to challenge/blame; more likely to protect position or ownership |

Stance and condition compose independently — e.g. Priya can be
`COLLABORATIVE + FRAZZLED` or `OPPOSITIONAL + NORMAL`. Either combination
must still read as Priya: temporary condition modifies the person, it does
not replace the person with a caricature.

## 4. Iteration-one rules

- **Power difficulty does not change move selection, stance, condition,
  repeated-move logic, or rendering.** It is parsed and logged (`power=...`)
  and nothing else for now — pure control metadata, established ahead of the
  later task that decides how it actually affects behaviour.
- **Relationship does not change move selection, stance, condition, power
  difficulty, repeated-move logic, or rendering.** It is parsed and logged
  (`relationship=...`) and remains permanently inert throughout actor
  generation. `BOSS` does deterministically gate the Managing Up repertoire
  (section 8), but only for the separate, explicit Coach path
  (`POST /v1/coach`) — never for actor generation.
- **Stance does not change move selection.** Temporary condition does not
  change move selection. They only change how the selected move is
  expressed.
- Move selection (`select_move`) is a deterministic, pure function of the
  latest user text — no LLM classifier, no second remote reasoning call —
  and stays independently testable.
- **Conversation context is a separate concept from temporary condition.**
  Don't use "state" ambiguously for both. The only conversation-context
  signal implemented is: did this actor's current move repeat the move from
  their immediately preceding turn? That signal may only vary wording, never
  move selection.
- There is no session database or store. Repeat detection is recomputed
  every request from the conversation history SillyTavern resends (see
  `previous_move_for_actor` in `arena_brain/engine.py`) — nothing is
  persisted. If it can't be determined from that history, it degrades
  safely to "no repeat detected" rather than failing. Don't introduce a
  persistence layer to support this — it's secondary to the core
  architecture.
- There is exactly **one** upstream remote LLM generation call per actor
  response.

## 5. Marker / control mechanism

Machine-control metadata arrives as bracketed markers inside message
content, e.g.:

```
[ARENA_ACTOR=priya]
[ARENA_POWER=amber]
[ARENA_RELATIONSHIP=boss]
[ARENA_STANCE=sceptical]
[ARENA_CONDITION=frazzled]
```

The brain detects these (`find_actor_id`, `find_power`, `find_relationship`,
`find_stance`, `find_condition`) and strips them (`strip_actor_markers`)
before the conversation is forwarded upstream — they are plumbing, never
dialogue. An empty value (`[ARENA_STANCE=]`), a missing marker, or an
unrecognised name all degrade safely to no override, not an error.

SillyTavern owns the user-facing control surface that sets these markers
(Quick Reply buttons / chat variables in the current MVP direction). No
custom UI, SillyTavern extension, or new frontend belongs in this repo to
support that.

## 6. Anti-regression rules

Do **not**:

- Move stable persona back into Python.
- Collapse persona, stance, condition and move into one giant prompt.
- Use free-text stance/condition controls.
- Infer stance or temporary condition using an LLM.
- Add an LLM call before the renderer.
- Make stance/condition affect move selection in iteration one.
- Let power difficulty influence move selection, stance, condition,
  repeated-move logic, rendering, or Coach behaviour until a later task
  explicitly authorises it. Iteration one is parsing, tracking, and logging
  only.
- Let relationship influence move selection, stance, condition, power
  difficulty, repeated-move logic, or rendering. It remains inert
  throughout actor generation permanently, not just "for now" — its only
  authorised downstream consumer is the Managing Up resolver (section 8).
- Conflate relationship (actor-to-user authority) with power difficulty
  (room-wide political difficulty). They are independent and must stay
  that way in code, config, and prompts.
- Add `SENIOR_STAKEHOLDER` or any other relationship value beyond
  `BOSS`/`PEER`/`DIRECT_REPORT` without a real scenario proving the current
  vocabulary is too coarse.
- Import `arena_brain.coaching` from `arena_brain/server.py`'s actor-
  generation path (`chat_completions`), or otherwise let Managing Up
  material reach `build_behavior_instruction()` or the actor's outbound
  prompt. Managing Up belongs exclusively to the Coach path (section 8),
  routed through `arena_brain/coach_api.py`.
- Turn the Managing Up repertoire into a six-item checklist a response must
  satisfy, or write it as a phrasebook of canned lines ("I appreciate your
  input...", "I hear what you're saying..."). It is a repertoire of logic
  the Coach draws one or two relevant items from, not a script.
- Make `POST /v1/coach` fire automatically after an actor response, add a
  classifier/reasoning call before it, chain a second call after it, or
  otherwise break the one-explicit-request-per-one-LLM-call guarantee for
  either path.
- Make "difficult" behaviour synonymous with hostility.
- Create one persona per stance/condition combination.
- Introduce session storage solely to support repeat-move behaviour.
- Duplicate SillyTavern functionality.
- Add RAG, a vector DB, an agent framework, Ollama, Docker, or other
  infrastructure to solve this problem.
- Sacrifice believable human behaviour for explicit/robotic behavioural
  labels — a good deterministic move can still render as generic
  facilitator-speak ("I appreciate you bringing this up...") if the
  rendering constraints and SillyTavern's own dialogue examples aren't
  doing their job. A correct move selection and a good rendering are two
  different kinds of correctness — don't conflate them when debugging.
- Build a generic "mega prompt builder" shared by the actor and Coach
  lanes, or combine their config directories. Shared *parsing* utilities in
  `arena_brain/engine.py` are fine; shared *behavioural prompt composition*
  is not (section 9).
- Let a model swap justify moving behaviour across the actor/Coach
  boundary. `ARENA_ACTOR_MODEL`/`ARENA_COACH_MODEL` change which renderer a
  lane uses, never which layer owns which behaviour (section 9).
- Let SillyTavern's `model` field win over `ARENA_ACTOR_MODEL`, or let
  Coach model selection depend on the incoming actor payload/model in any
  way (section 9).
- Silently retry a rejected configured model against the default. Model
  access failures must surface visibly (section 9).
- Validate `ARENA_ACTOR_MODEL`/`ARENA_COACH_MODEL` against a hardcoded list
  of known OpenAI models. Account/project access changes over time.

## 7. Worked example

```
Priya persona (SillyTavern character card)
  + SCEPTICAL          (stance: withhold agreement, probe the reasoning)
  + FRAZZLED            (condition: less patience, less social cushioning)
  + CLARIFY_BLOCKER      (move: check whether the concern truly blocks progress)
  →
  Still Priya. Less socially cushioned than her baseline, slower to accept
  the premise at face value than she'd normally be — but making the same
  strategic move a calm Priya would make: checking whether this actually
  stops the work, or whether it can be managed alongside it.
```

The exact sentence the LLM renders is not part of this architecture — only
the composition (persona + stance + condition + move) and the constraint
that the move stays legible through all of it.

## 8. Managing Up and the Coach path (MVP implemented)

**Relationship and Managing Up are not the same thing — do not conflate
them:**

| | Relationship | Managing Up |
|---|---|---|
| What it is | Factual actor-to-user authority metadata | A Coach-side behavioural evaluation lens |
| Where it lives | `arena_brain/engine.py` (`find_relationship`), consumed by the actor-generation path (for routing/logging only — inert otherwise) | `arena_brain/coaching.py`, consumed by the Coach path (`arena_brain/coach_api.py`) |
| What it evaluates | Nothing — it's a label | How the **user** communicated with an actor who has formal authority over them |
| Activation | Set explicitly via `[ARENA_RELATIONSHIP=...]` | Deterministically derived: active only when `relationship == BOSS` |

Managing Up is **not** actor persona, stance, condition, power difficulty,
an actor conversational move, or a political-event classifier. It does not
appear as another layer in the actor-generation composition stack in
section 1 — it lives entirely in the separate, explicit Coach path:

```
ACTOR PATH (unchanged by this task)

  SillyTavern → POST /v1/chat/completions
    Persona + Power + Relationship metadata + Stance + Condition + Move
    → actor rendering (one LLM call)


COACH PATH (this task's MVP — POST /v1/coach, explicit user action only)

  deterministic context assembly (arena_brain/coaching.py::build_coach_context):
    up to 8 most recent user/assistant messages (system messages excluded,
    machine-control markers stripped, order preserved)
    + current actor (find_actor_id)
    + current relationship (find_relationship)
    + the user's latest utterance, verbatim (latest_user_text)

  deterministic prompt assembly (arena_brain/coaching.py::build_coach_prompt):
    generic Coach rubric
    + if relationship == BOSS: the Managing Up repertoire
    + the assembled context, with the verbatim utterance delimited

  → exactly one Coach LLM call (arena_brain/coach_api.py)
  → one concise coaching observation, JSON: {"feedback": "...", ...}
```

Both call paths use the same model (`gpt-4o-mini`) and the same
`OPENAI_API_KEY`, but they are two entirely separate, explicitly-triggered
requests — Coach never fires automatically after an actor response, and
never chains a second call after itself.

**The Managing Up repertoire** (`config/coach/managing_up.yaml`) is six
canonical principles, each capturing a piece of communication *logic*, not
canned phrasing:

| Principle | Logic |
|---|---|
| `ALIGN_BEFORE_CHALLENGE` | Briefly recognise the boss's direction/authority before presenting a different view — alignment signalling, not automatic agreement |
| `CLARIFY_PRIORITY` | When instructions or priorities conflict, make the decision point explicit rather than silently absorbing incompatible directions |
| `STATE_CONSTRAINT` | State a genuine constraint/risk/trade-off factually and concisely — decision-quality information, not self-justification |
| `OFFER_OPTIONS` | Give workable choices or a recommendation rather than just a problem — preserve the boss's decision authority |
| `PROTECT_ACCOUNTABILITY` | Make ownership and changed responsibilities explicit when necessary, without becoming territorial |
| `CONFIRM_AND_RECORD` | Close material discussions with a clear decision, owner, and next action; selective written follow-up when direction/accountability materially changes |

**This is a repertoire, not a checklist.** A good user response typically
draws on one or two of these, not all six. The Coach identifies the single
most relevant missed or effective behaviour, never a six-point scorecard.
Believable human communication matters more than mechanically demonstrating
a framework — the Coach is explicitly instructed not to invent a flaw just
because it was invoked, and to say briefly what worked when a short reply
(e.g. "Yep, will do.") was already adequate.

`get_managing_up_guidance(relationship_name)` returns the full
`{PRINCIPLE: guidance}` mapping when `relationship_name == "BOSS"`, and
`None` (never an empty dict — consistent with how every other layer signals
"no override" in this codebase) for `PEER`, `DIRECT_REPORT`, missing, or
unknown relationships. It is deterministic, has no LLM call of its own, and
is still not imported anywhere in `POST /v1/chat/completions` — the actor
path is structurally unaffected by the Coach path's existence.

**MVP scope, deliberately not built here:** Coach scoring, numerical
ratings, skill histories, session storage, automatic/implicit Coach
invocation, a Coach UI or SillyTavern Quick Reply, power-difficulty or
stance/condition Coach logic, and full-conversation summarisation. These
are later tasks.

## 9. Two behaviour lanes and independent model configuration

Sections 1–8 describe *what* each layer owns. This section makes explicit
*where the line is drawn* between the two behaviour lanes that exist in
this codebase, and states that each lane's remote model is an independent,
swappable execution detail — never a reason to move behavioural ownership
across the line.

```
ACTOR LANE                                  COACH LANE

Purpose: generate believable               Purpose: evaluate the USER'S
colleague dialogue                         communication, one observation

SillyTavern persona                        recent stripped conversation
+ Power metadata                           + user's latest response, verbatim
+ Relationship metadata                    + actor ID where available
+ Stance                                   + Relationship
+ Condition                                + generic Coach rubric
+ deterministic Move                       + Managing Up repertoire (BOSS only)
+ lightweight (repeated-move) context
        ↓                                          ↓
   ARENA_ACTOR_MODEL                          ARENA_COACH_MODEL
   (default gpt-4o-mini)                      (default gpt-4o-mini)
        ↓                                          ↓
believable colleague response              one useful coaching observation

Code: arena_brain/engine.py,               Code: arena_brain/coaching.py,
build_behavior_instruction(),              build_coach_context(),
move/stance/condition config,              build_coach_prompt(),
SillyTavern persona cards                  arena_brain/coach_api.py,
                                            config/coach/
Endpoint: POST /v1/chat/completions        Endpoint: POST /v1/coach
                                            (explicit user action only)
```

**The actor lane must never consume:** the Managing Up repertoire, the
generic Coach rubric, coaching feedback instructions, any evaluation of the
user's communication, or `ARENA_COACH_MODEL`.

**The Coach lane must never consume:** actor move selection or its
guidance, stance/condition rendering guidance, actor persona construction,
repeated-move logic, or `ARENA_ACTOR_MODEL`.

Shared low-level utilities are fine where genuinely generic (both lanes
reuse `find_actor_id`, `find_relationship`, `latest_user_text`,
`strip_actor_markers_from_messages`, `load_named_guidance` from
`arena_brain/engine.py` — none of these are behavioural, they're parsing).
What must **never** be shared is behavioural prompt composition: there is
no generic "mega prompt builder", and Actor and Coach configuration
(`config/moves/`, `config/stances/`, `config/conditions/` vs.
`config/coach/`) are never combined.

**Model configuration** (`arena_brain/settings.py`):

| | Env var | Default | Used by |
|---|---|---|---|
| Actor model | `ARENA_ACTOR_MODEL` | `gpt-4o-mini` | `POST /v1/chat/completions` |
| Coach model | `ARENA_COACH_MODEL` | `gpt-4o-mini` | `POST /v1/coach` |

Missing or blank (after stripping whitespace) falls back to the default.
Arbitrary model identifiers are accepted without validation against a
hardcoded list — which models an OpenAI account/project can actually use
changes over time, and this code must not assume otherwise.

**Meeting Arena Brain, not SillyTavern, is authoritative for the actor
model.** Whatever `model` value SillyTavern sends in the incoming
`/v1/chat/completions` payload is overwritten with `ARENA_ACTOR_MODEL`, not
negotiated with — this avoids the Brain and SillyTavern fighting over model
selection. Coach model selection is entirely independent of both: it never
reads the incoming payload's `model` field and never depends on
`ARENA_ACTOR_MODEL`.

**No silent fallback.** If a configured model is rejected upstream (e.g.
the OpenAI account/project lacks access to it), that failure must surface
as a normal `502`, not be swallowed and silently retried against
`gpt-4o-mini`. A silent fallback would make model-quality benchmarking
(the reason this configuration exists) actively misleading. Solving OpenAI
account/project access itself is out of scope here — this only guarantees
the failure is visible.

**Model choice is an execution/configuration concern, not a behavioural
ownership concern.** A stronger Coach model never justifies moving actor
behaviour, persona, or move selection into the Coach lane. A cheaper actor
model never justifies leaking coaching logic into the actor prompt.
Changing `ARENA_ACTOR_MODEL` or `ARENA_COACH_MODEL` changes which
renderer/reasoner a lane uses — it must never change which layer owns which
behaviour.

`GET /v1/models` reports the currently configured actor model only (what
SillyTavern's connection settings expect to see) — Coach is deliberately
**not** exposed there as another selectable chat model; it remains a
separate endpoint. `GET /health` additionally reports both
`actor_model` and `coach_model` for a quick manual check before a
benchmarking run, without overloading the SillyTavern-facing endpoint.
