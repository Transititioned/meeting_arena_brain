from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any

from arena_brain.actors import ACTORS


class Move(StrEnum):
    CLARIFY_BLOCKER = "CLARIFY_BLOCKER"
    ACKNOWLEDGE_THEN_REFRAME = "ACKNOWLEDGE_THEN_REFRAME"
    SURFACE_TRADEOFF = "SURFACE_TRADEOFF"
    PROTECT_ACCOUNTABILITY = "PROTECT_ACCOUNTABILITY"
    ASK_FOR_SPECIFICS = "ASK_FOR_SPECIFICS"


ACTOR_MARKER_RE = re.compile(r"\[ARENA_ACTOR=(priya|marcus|dana)\]", re.IGNORECASE)
STANCE_MARKER_RE = re.compile(r"\[ARENA_STANCE=([A-Za-z_]*)\]", re.IGNORECASE)
CONDITION_MARKER_RE = re.compile(r"\[ARENA_CONDITION=([A-Za-z_]*)\]", re.IGNORECASE)
POWER_MARKER_RE = re.compile(r"\[ARENA_POWER=([A-Za-z_]*)\]", re.IGNORECASE)
VALID_POWER_LEVELS = frozenset({"GREEN", "AMBER", "RED"})

RULES: tuple[tuple[Move, tuple[str, ...]], ...] = (
    (
        Move.CLARIFY_BLOCKER,
        (
            "block",
            "blocker",
            "ready",
            "readiness",
            "risk",
            "stop us",
            "prevent",
            "resolved yet",
            "not resolved",
            "unresolved",
        ),
    ),
    (
        Move.SURFACE_TRADEOFF,
        (
            "priority",
            "instead",
            "delay",
            "defer",
            "trade-off",
            "tradeoff",
            "slips",
        ),
    ),
    (
        Move.PROTECT_ACCOUNTABILITY,
        (
            "owner",
            "ownership",
            "responsible",
            "agreed",
            "agreement",
            "said",
            "sign-off",
        ),
    ),
    (
        Move.ACKNOWLEDGE_THEN_REFRAME,
        (
            "disagree",
            "don't agree",
            "do not agree",
            "however",
            "concern",
            "but",
        ),
    ),
)


def select_move(text: str) -> Move:
    normalized = text.lower()
    for move, keywords in RULES:
        if any(keyword in normalized for keyword in keywords):
            return move
    return Move.ASK_FOR_SPECIFICS


def parse_actor_marker(text: str) -> str | None:
    match = ACTOR_MARKER_RE.search(text)
    if not match:
        return None
    return match.group(1).lower()


def parse_stance_marker(text: str) -> str | None:
    match = STANCE_MARKER_RE.search(text)
    if not match or not match.group(1):
        return None
    return match.group(1).upper()


def parse_condition_marker(text: str) -> str | None:
    match = CONDITION_MARKER_RE.search(text)
    if not match or not match.group(1):
        return None
    return match.group(1).upper()


def parse_power_marker(text: str) -> str | None:
    """Parse [ARENA_POWER=...]. Unlike stance/condition, an unrecognised
    value resolves to None here (not just at guidance lookup) - power's
    closed vocabulary is enforced at parse time, same as actor markers."""
    match = POWER_MARKER_RE.search(text)
    if not match or not match.group(1):
        return None
    value = match.group(1).upper()
    return value if value in VALID_POWER_LEVELS else None


def strip_actor_markers(text: str) -> str:
    text = ACTOR_MARKER_RE.sub("", text)
    text = STANCE_MARKER_RE.sub("", text)
    text = CONDITION_MARKER_RE.sub("", text)
    text = POWER_MARKER_RE.sub("", text)
    return text.strip()


def strip_actor_markers_from_messages(
    messages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            message = {**message, "content": strip_actor_markers(content)}
        cleaned.append(message)
    return cleaned


def find_actor_id(messages: list[dict[str, Any]]) -> str | None:
    """Identify the actor whose turn this is: the LATEST message carrying a
    recognised actor marker, not the first one in history. With the
    repeated-move feature resending every past turn's marker, earlier turns
    routinely belong to other actors, so a forward scan would misidentify
    the current speaker in any multi-actor conversation.
    """
    for message in reversed(messages):
        content = message.get("content")
        if isinstance(content, str):
            actor_id = parse_actor_marker(content)
            if actor_id in ACTORS:
                return actor_id
    return None


def find_stance(messages: list[dict[str, Any]]) -> str | None:
    for message in reversed(messages):
        content = message.get("content")
        if isinstance(content, str):
            stance = parse_stance_marker(content)
            if stance:
                return stance
    return None


def find_condition(messages: list[dict[str, Any]]) -> str | None:
    for message in reversed(messages):
        content = message.get("content")
        if isinstance(content, str):
            condition = parse_condition_marker(content)
            if condition:
                return condition
    return None


def find_power(messages: list[dict[str, Any]]) -> str | None:
    """Scenario-level power-difficulty marker: GREEN/AMBER/RED, latest
    applicable (recognised) marker wins. Control metadata only in this
    iteration - see SEMANTIC_ARCHITECTURE.md."""
    for message in reversed(messages):
        content = message.get("content")
        if isinstance(content, str):
            power = parse_power_marker(content)
            if power:
                return power
    return None


def latest_user_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user" and isinstance(message.get("content"), str):
            return strip_actor_markers(message["content"])
    return ""


def previous_move_for_actor(messages: list[dict[str, Any]], actor_id: str) -> Move | None:
    """Deterministically recompute the move this actor's previous turn triggered.

    No move history is stored anywhere: SillyTavern resends the full
    conversation on every call, and each of the actor's own earlier turns is
    still marked with `[ARENA_ACTOR=...]` in that resent history, so re-running
    `select_move` over the second-to-last one reproduces exactly what fired
    for it originally.
    """
    own_texts: list[str] = []
    for message in messages:
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        if parse_actor_marker(content) == actor_id:
            own_texts.append(strip_actor_markers(content))

    if len(own_texts) < 2:
        return None
    return select_move(own_texts[-2])


def load_named_guidance(path: Path) -> dict[str, str]:
    guidance: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        if not raw_line.startswith((" ", "\t")) and raw_line.endswith(":"):
            if current_key is not None:
                guidance[current_key] = " ".join(current_lines).strip()
            current_key = raw_line[:-1]
            current_lines = []
            continue
        if current_key is not None:
            current_lines.append(raw_line.strip())

    if current_key is not None:
        guidance[current_key] = " ".join(current_lines).strip()
    return guidance


def load_move_guidance(path: Path) -> dict[Move, str]:
    return {Move(name): guidance for name, guidance in load_named_guidance(path).items()}


def build_behavior_instruction(
    selected_move: Move,
    move_guidance: str,
    stance_guidance: str | None = None,
    condition_guidance: str | None = None,
    repeated_move: bool = False,
) -> str:
    parts = ["Meeting Arena behavioural instruction."]
    if stance_guidance:
        parts.append(f"Current stance: {stance_guidance}")
    if condition_guidance:
        parts.append(f"Temporary condition: {condition_guidance}")
    parts.append(f"Selected move: {selected_move.value}.")
    parts.append(f"Move guidance: {move_guidance}.")
    if repeated_move:
        parts.append(
            "This is the same conversational move the actor used last turn: "
            "vary the wording and sentence structure noticeably, do not repeat "
            "the same phrasing."
        )
    parts.append(
        "Rendering constraints: normal workplace language; no theatrical roleplay; "
        "no caricature; do not announce personality traits; pressure should often "
        "remain implicit; react to what was actually said; maximum 1-2 short paragraphs."
    )
    return " ".join(parts)

