from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arena_brain.engine import (
    VALID_POWER_LEVELS,
    find_actor_id,
    find_power,
    find_relationship,
    latest_user_text,
    load_named_guidance,
    strip_actor_markers_from_messages,
)

ROOT = Path(__file__).resolve().parents[1]
MANAGING_UP_GUIDANCE: dict[str, str] = load_named_guidance(
    ROOT / "config" / "coach" / "managing_up.yaml"
)

_POWER_PROTECTION_RAW: dict[str, str] = load_named_guidance(
    ROOT / "config" / "coach" / "power_protection.yaml"
)
# power_protection.yaml holds two logically distinct things in one flat
# file: the level-independent repertoire (8 principles) and the
# level-specific sensitivity note (GREEN/AMBER/RED, same closed vocabulary
# as config/power/power.yaml). Split them here rather than in the config
# file, since load_named_guidance() only knows flat KEY: text pairs.
POWER_SENSITIVITY: dict[str, str] = {
    level: _POWER_PROTECTION_RAW[level] for level in VALID_POWER_LEVELS
}
POWER_PROTECTION_GUIDANCE: dict[str, str] = {
    name: guidance
    for name, guidance in _POWER_PROTECTION_RAW.items()
    if name not in VALID_POWER_LEVELS
}

RECENT_CONTEXT_LIMIT = 8

GENERIC_COACH_RULES = (
    "You are the Meeting Arena Coach: an experienced, practical, politically "
    "aware workplace communication coach. Give the user exactly ONE useful "
    "piece of feedback on their latest response - either what worked, or the "
    "single most important missed opportunity. Consider, where relevant: "
    "clarity, relational signalling, tact, boundaries/accountability, "
    "authority/hierarchy sensitivity, action orientation, excessive "
    "explanation, and whether the response actually addressed what was "
    "said. Do not require every quality to be demonstrated, and do not "
    "score or produce a checklist. Be concise: usually 2-4 sentences, no "
    "more than about 100 words. Do not sound therapeutic, psychoanalyse, "
    "infer hidden motives as fact, manufacture political conflict, nitpick "
    "an already-adequate concise response, or over-praise. If the response "
    "already worked, say briefly what worked - do not invent a flaw just "
    "because Coach was invoked. Do not expose internal principle names "
    "unless doing so genuinely helps. Never lecture or rewrite the "
    "conversation."
)


def get_managing_up_guidance(relationship_name: str | None) -> dict[str, str] | None:
    """Managing Up is a Coach-side evaluation lens, not an actor-generation
    layer: it concerns how the USER communicates with an actor who holds
    formal authority over them, activated only when relationship == BOSS.
    PEER, DIRECT_REPORT, missing, and unknown relationships all resolve to
    None (never an empty dict) - matching how absence is signalled
    elsewhere in this codebase (find_power/find_relationship/
    STANCE_GUIDANCE.get(...)).

    Not consumed anywhere in the actor-generation path
    (arena_brain/server.py::chat_completions) - relationship stays
    permanently inert there. This is the sole consumer, called from the
    explicit Coach path (arena_brain/coach_api.py). See
    SEMANTIC_ARCHITECTURE.md.
    """
    if relationship_name != "BOSS":
        return None
    return MANAGING_UP_GUIDANCE


def get_power_protection_guidance(power_name: str | None) -> dict[str, str] | None:
    """Power Protection is a Coach-side evaluation lens keyed on power
    difficulty (room-wide), not relationship (actor-to-user) - it applies
    regardless of which actor the user is talking to. GREEN, AMBER, and RED
    all activate the SAME repertoire (8 principles); only the sensitivity
    note (get_power_sensitivity) varies by level. Missing or unrecognised
    power resolves to None, same "no override" convention as everywhere
    else in this codebase. Never consumed by actor generation - see
    SEMANTIC_ARCHITECTURE.md.
    """
    if power_name not in VALID_POWER_LEVELS:
        return None
    return POWER_PROTECTION_GUIDANCE


def get_power_sensitivity(power_name: str | None) -> str | None:
    """What the Coach should pay more attention to at this power-difficulty
    level. Power difficulty changes the Coach's SENSITIVITY to
    consequences, never its licence to speculate - it must never be used to
    assert motive the transcript doesn't actually support. See
    build_coach_prompt(), which pairs this with that guardrail explicitly.
    """
    if power_name not in VALID_POWER_LEVELS:
        return None
    return POWER_SENSITIVITY.get(power_name)


@dataclass(frozen=True)
class CoachContext:
    actor_id: str | None
    relationship_name: str | None
    power_name: str | None
    recent_context: list[dict[str, Any]]
    latest_user_utterance: str


def build_coach_context(
    messages: list[dict[str, Any]], limit: int = RECENT_CONTEXT_LIMIT
) -> CoachContext:
    """Deterministically derive everything the Coach needs from the raw
    SillyTavern/OpenAI-style message history - no LLM call, no inference.

    Reuses the same, already-tested marker-parsing functions the actor path
    uses (find_actor_id/find_relationship/latest_user_text), so behaviour
    stays identical to how those markers are read everywhere else. The
    recent-context window is capped at `limit` dialogue (user/assistant)
    messages, system messages excluded, markers stripped, order preserved -
    a deliberately small window for token/latency control, not a summary.
    """
    actor_id = find_actor_id(messages)
    relationship_name = find_relationship(messages)
    power_name = find_power(messages)
    latest_user_utterance = latest_user_text(messages)

    dialogue = [
        message
        for message in messages
        if message.get("role") in ("user", "assistant")
        and isinstance(message.get("content"), str)
    ]
    recent_context = strip_actor_markers_from_messages(dialogue)[-limit:]

    return CoachContext(
        actor_id=actor_id,
        relationship_name=relationship_name,
        power_name=power_name,
        recent_context=recent_context,
        latest_user_utterance=latest_user_utterance,
    )


def build_coach_prompt(context: CoachContext) -> list[dict[str, str]]:
    """Build the Coach's own one-off prompt. Deliberately separate from
    build_behavior_instruction(), which remains actor-rendering-only."""
    managing_up = get_managing_up_guidance(context.relationship_name)
    power_protection = get_power_protection_guidance(context.power_name)
    power_sensitivity = get_power_sensitivity(context.power_name)

    system_parts = [GENERIC_COACH_RULES]
    if managing_up:
        principle_lines = " ".join(
            f"{name}: {guidance}" for name, guidance in managing_up.items()
        )
        system_parts.append(
            "The current actor has formal managerial authority over the "
            "user (BOSS relationship). Also draw on these Managing Up "
            "principles where relevant, using at most one or two, not all "
            "of them: " + principle_lines
        )
    if power_protection:
        principle_lines = " ".join(
            f"{name}: {guidance}" for name, guidance in power_protection.items()
        )
        system_parts.append(
            f"Power difficulty in this scenario is {context.power_name}. "
            f"{power_sensitivity} Power difficulty changes your sensitivity "
            "to consequences, never your licence to speculate: it does not "
            "prove motive on its own, and any political read must still be "
            "supported by what the transcript actually shows. Where "
            "relevant, draw on this Power Protection repertoire, using at "
            "most one or two items, not all of them: " + principle_lines
        )

    context_lines: list[str] = []
    if context.actor_id:
        context_lines.append(f"Current actor: {context.actor_id}")
    if context.relationship_name:
        context_lines.append(f"Relationship: {context.relationship_name}")
    if context.power_name:
        context_lines.append(f"Power difficulty: {context.power_name}")

    context_lines.append("")
    context_lines.append("Recent conversation:")
    if context.recent_context:
        for message in context.recent_context:
            role = message.get("role", "user")
            context_lines.append(f"{role}: {message.get('content', '')}")
    else:
        context_lines.append("(no prior context)")

    context_lines.append("")
    context_lines.append("User's exact latest response:")
    context_lines.append("<<<")
    context_lines.append(context.latest_user_utterance)
    context_lines.append(">>>")

    return [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user", "content": "\n".join(context_lines)},
    ]
