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

## 2. Ownership boundaries

| Concern | Owner | Where |
|---|---|---|
| Stable persona (who someone is, voice, cadence, normal challenge style, dialogue examples) | SillyTavern | The character card, not this repo |
| Stance (attitude toward the current proposal) | This repo, rendering overlay | `config/stances/stances.yaml` |
| Temporary condition (what kind of day/moment the actor is having) | This repo, rendering overlay | `config/conditions/conditions.yaml` |
| Move selection (the strategic conversational action) | This repo, deterministic Python | `arena_brain/engine.py::select_move` |
| Natural wording | The remote LLM | One call per actor response |

The actor ID (`priya` / `marcus` / `dana`) stays in the brain purely for
**routing**: which move guidance applies, which repeated-move history to
check, whose turn this is. It is not a vehicle for persona text. The brain
must not become a second persona engine — do not inject a behavioural
profile (authority, pace, warmth, etc.) into the prompt it builds. That
description belongs in the SillyTavern character card.

## 3. Closed vocabularies

Stance and temporary condition are each a small, closed, named vocabulary —
never free text, never LLM-inferred. An unrecognised or missing value
degrades safely to no override.

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
[ARENA_STANCE=sceptical]
[ARENA_CONDITION=frazzled]
```

The brain detects these (`find_actor_id`, `find_stance`, `find_condition`)
and strips them (`strip_actor_markers`) before the conversation is
forwarded upstream — they are plumbing, never dialogue. An empty value
(`[ARENA_STANCE=]`), a missing marker, or an unrecognised name all degrade
safely to no override, not an error.

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
