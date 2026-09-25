# meeting_arena_brain

Local deterministic reasoning layer for Meeting Arena. It exposes a small
OpenAI-compatible proxy for SillyTavern, chooses a deterministic conversational
move from the latest user utterance, injects one compact behavioural instruction,
and forwards the request to OpenAI `gpt-4o-mini`.

> **Before changing persona, power difficulty, relationship, stance,
> condition, move selection, prompt composition, or Managing Up/Coach
> behaviour, read [`SEMANTIC_ARCHITECTURE.md`](SEMANTIC_ARCHITECTURE.md).**
> It is the authoritative record of which layer owns what, and a lot of
> iterative work went into keeping those layers separate — please don't
> re-merge them without reading it first.

## Windows setup

Run these commands from the repository root.

Command Prompt (cmd.exe):

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell's prompt doesn't show a `(.venv)` prefix after activating, that's
usually just a custom prompt (oh-my-posh, Starship, a `$PROFILE` script)
overriding it — activation still worked if `Get-Command python` resolves to
`.venv\Scripts\python.exe`.

Supply the OpenAI key locally without committing it. The app does **not**
load `.env` automatically — set the real key as an environment variable in
the same terminal session you run the server from.

Command Prompt (cmd.exe):

```cmd
set OPENAI_API_KEY=sk-your-real-key
```

PowerShell:

```powershell
$env:OPENAI_API_KEY="sk-your-real-key"
```

`.env.example` is only a template for keeping the key somewhere locally if
you want one; copying it to `.env` does not make the app read it:

```cmd
copy .env.example .env
notepad .env
```

Never commit `.env`.

## Run locally

```cmd
scripts\run-brain.cmd
```

The service listens on:

```text
http://127.0.0.1:8765
```

Health and model endpoints:

```text
GET http://127.0.0.1:8765/health
GET http://127.0.0.1:8765/v1/models
```

## SillyTavern connection

Use an OpenAI-compatible chat completion connection:

```text
API type: Chat Completions / OpenAI-compatible
Base URL: http://127.0.0.1:8765/v1
Model: gpt-4o-mini
API key: any placeholder value in SillyTavern; the proxy reads OPENAI_API_KEY locally
Streaming: OFF
```

This proxy does not support streaming responses yet. Leave Streaming off in
SillyTavern's connection settings — a `stream: true` request is rejected
with a clear `400` error rather than being silently mishandled.

Actor, power, relationship, stance, and condition markers are stripped
before the conversation is forwarded to OpenAI; they are plumbing for the
brain, not dialogue. Include one actor marker somewhere in the incoming
conversation:

```text
[ARENA_ACTOR=priya]
[ARENA_ACTOR=marcus]
[ARENA_ACTOR=dana]
```

If no recognised marker is present, the proxy still forwards the request with
minimal modification.

### Power difficulty (optional, metadata only for now)

Power difficulty is a scenario-level control marker describing how
politically difficult the room is — independent of any actor's persona,
stance, or condition:

```text
[ARENA_POWER=green]
[ARENA_POWER=amber]
[ARENA_POWER=red]
```

Valid values and their definitions live in `config/power/power.yaml` — a
closed vocabulary, same as stance and condition. An unrecognised or omitted
value is treated as no override.

**This is plumbing only in this iteration.** The marker is parsed, the
latest applicable one in history wins, it's stripped before forwarding
upstream, and it's logged (`power=GREEN` / `power=AMBER` / `power=RED` /
`power=none`) — but it does not yet affect move selection, stance,
condition, repeated-move logic, or the LLM prompt in any way. See
`SEMANTIC_ARCHITECTURE.md` for the full rationale.

### Relationship / authority (optional, metadata only for now)

Relationship is **actor-to-user** metadata — the current actor's formal
authority relationship to the user, not a room-wide scenario property (that's
power difficulty; see above). In one multi-person meeting different actors
can carry different relationship values while power difficulty stays
constant for the room:

```text
[ARENA_RELATIONSHIP=boss]
[ARENA_RELATIONSHIP=peer]
[ARENA_RELATIONSHIP=direct_report]
```

Valid values and their definitions live in `config/relationships/relationships.yaml`
— a closed vocabulary, same as power/stance/condition. An unrecognised or
omitted value is treated as no override.

**Relationship remains permanently inert in actor generation.** The marker
is parsed, the latest applicable one in history wins, it's stripped before
forwarding upstream, and it's logged (`relationship=BOSS` / `PEER` /
`DIRECT_REPORT` / `none`) — but it never affects move selection, stance,
condition, power difficulty, repeated-move logic, or the actor's own LLM
prompt (`POST /v1/chat/completions`).

Its one downstream use is the Managing Up resolver, consumed by the
separate `POST /v1/coach` endpoint below: `BOSS` deterministically
activates the Managing Up coaching repertoire in that Coach prompt. See
`SEMANTIC_ARCHITECTURE.md` for the full rationale.

## Coach (on-demand, `POST /v1/coach`)

An explicit, separate endpoint — never called automatically after an actor
response. Given the same SillyTavern-style `messages` history, it derives
actor/relationship from the existing markers, builds a small deterministic
context window (up to the most recent 8 user/assistant messages, markers
stripped, system messages excluded), and makes exactly one LLM call to give
one concise (~100 word) coaching observation. When the current actor's
relationship is `BOSS`, the Managing Up repertoire is included; otherwise
the Coach still gives generic communication feedback.

Request:

```json
{ "messages": [ { "role": "user", "content": "[ARENA_ACTOR=priya] [ARENA_RELATIONSHIP=boss] Yep, will do." } ] }
```

Response:

```json
{ "feedback": "...", "relationship": "BOSS", "actor": "priya" }
```

Manual test from PowerShell (server must already be running via
`scripts\run-brain.cmd`, and `OPENAI_API_KEY` must be set to a real key for
a real response — this will make one live OpenAI call):

```powershell
$body = @{
    messages = @(
        @{ role = "user"; content = "[ARENA_ACTOR=priya] [ARENA_RELATIONSHIP=boss] Yep, will do." }
    )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
    -Method Post `
    -Uri http://127.0.0.1:8765/v1/coach `
    -ContentType "application/json" `
    -Body $body
```

### Stance and temporary condition (optional)

Stance is an explicit, scenario-level overlay; temporary condition is a
shorter-lived, per-scene modifier. Both are set explicitly — the brain never
infers them — and both affect only how the response is rendered, not which
conversational move is selected. Add either marker alongside the actor
marker:

```text
[ARENA_STANCE=neutral]
[ARENA_STANCE=collaborative]
[ARENA_STANCE=sceptical]
[ARENA_STANCE=oppositional]

[ARENA_CONDITION=normal]
[ARENA_CONDITION=pressured]
[ARENA_CONDITION=frazzled]
[ARENA_CONDITION=defensive]
```

Valid values and their guidance text live in `config/stances/stances.yaml`
and `config/conditions/conditions.yaml`. Both are closed vocabularies —
extend them there, not with free text. An unrecognised or omitted value is
treated as no override (`NEUTRAL`/`NORMAL`).

The actor's persona lives in SillyTavern's own character definition, not in
this repo — the brain only plumbs the actor ID through to select a move and
look up stance/condition guidance; it does not inject any persona
description of its own into the behavioural instruction.

The brain also tracks, without any stored state, whether the current move is
the same one this actor used on their immediately preceding turn (by
deterministically re-running move selection over that turn from the resent
conversation history). When it is, the rendering instruction is told to vary
the wording rather than repeat it — move selection itself is unaffected.
This depends on SillyTavern resending each historical turn's actor marker,
not just the newest one; the server logs `previous_move=...` on every
request so this can be checked against real traffic rather than assumed.

## Tests

```cmd
pytest
```
