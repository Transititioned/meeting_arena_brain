# meeting_arena_brain

Local deterministic reasoning layer for Meeting Arena. It exposes a small
OpenAI-compatible proxy for SillyTavern, chooses a deterministic conversational
move from the latest user utterance, injects one compact behavioural instruction,
and forwards the request to OpenAI `gpt-4o-mini`.

## Windows setup

Run these commands from the repository root:

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

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

Actor, stance, and condition markers are stripped before the conversation is
forwarded to OpenAI; they are plumbing for the brain, not dialogue. Include
one actor marker somewhere in the incoming conversation:

```text
[ARENA_ACTOR=priya]
[ARENA_ACTOR=marcus]
[ARENA_ACTOR=dana]
```

If no recognised marker is present, the proxy still forwards the request with
minimal modification.

### Stance and temporary condition (optional)

Stance is an explicit, scenario-level overlay on an actor's baseline
persona; temporary condition is a shorter-lived, per-scene modifier. Both
are set explicitly — the brain never infers them — and both affect only how
the response is rendered, not which conversational move is selected. Add
either marker alongside the actor marker:

```text
[ARENA_STANCE=guarded]
[ARENA_STANCE=cooperative]
[ARENA_STANCE=escalated]

[ARENA_CONDITION=rushed]
[ARENA_CONDITION=frustrated]
[ARENA_CONDITION=distracted]
```

Valid values and their guidance text live in `config/stances/stances.yaml`
and `config/conditions/conditions.yaml`. Both are closed vocabularies —
extend them there, not with free text. An unrecognised or omitted value is
treated as no override (`NEUTRAL`).

The brain also tracks, without any stored state, whether the current move is
the same one this actor used on their immediately preceding turn (by
deterministically re-running move selection over that turn from the resent
conversation history). When it is, the rendering instruction is told to vary
the wording rather than repeat it — move selection itself is unaffected.

## Tests

```cmd
pytest
```
