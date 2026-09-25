from __future__ import annotations

import os

DEFAULT_ACTOR_MODEL = "gpt-4o-mini"
DEFAULT_COACH_MODEL = "gpt-4o-mini"


def _resolve_model(env_var: str, default: str) -> str:
    value = os.getenv(env_var, "").strip()
    return value or default


def get_actor_model() -> str:
    """The OpenAI model the actor lane (POST /v1/chat/completions) sends
    upstream. Independently configurable via ARENA_ACTOR_MODEL so actor and
    Coach model quality can be benchmarked separately, with no SillyTavern
    changes required. Read fresh on every call (not cached at import time)
    so it can be overridden per process/test without a restart. Missing or
    blank (after stripping whitespace) falls back to DEFAULT_ACTOR_MODEL.
    No validation against a hardcoded OpenAI model list - which models an
    account/project can actually use changes over time and is an
    operational concern, not something this code should assume."""
    return _resolve_model("ARENA_ACTOR_MODEL", DEFAULT_ACTOR_MODEL)


def get_coach_model() -> str:
    """The OpenAI model the Coach lane (POST /v1/coach) sends upstream.
    Independently configurable via ARENA_COACH_MODEL - see
    get_actor_model() for the resolution rules, which are identical. If the
    configured Coach model is rejected upstream, that failure must surface
    normally (502) rather than silently retrying with the default - a
    silent fallback would make model benchmarking misleading."""
    return _resolve_model("ARENA_COACH_MODEL", DEFAULT_COACH_MODEL)
