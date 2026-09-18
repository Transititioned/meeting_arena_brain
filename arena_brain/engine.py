from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any

from arena_brain.actors import ACTORS, ActorProfile


class Move(StrEnum):
    CLARIFY_BLOCKER = "CLARIFY_BLOCKER"
    ACKNOWLEDGE_THEN_REFRAME = "ACKNOWLEDGE_THEN_REFRAME"
    SURFACE_TRADEOFF = "SURFACE_TRADEOFF"
    PROTECT_ACCOUNTABILITY = "PROTECT_ACCOUNTABILITY"
    ASK_FOR_SPECIFICS = "ASK_FOR_SPECIFICS"


ACTOR_MARKER_RE = re.compile(r"\[ARENA_ACTOR=(priya|marcus|dana)\]", re.IGNORECASE)

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


def strip_actor_markers(text: str) -> str:
    return ACTOR_MARKER_RE.sub("", text).strip()


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
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            actor_id = parse_actor_marker(content)
            if actor_id in ACTORS:
                return actor_id
    return None


def latest_user_text(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user" and isinstance(message.get("content"), str):
            return strip_actor_markers(message["content"])
    return ""


def load_move_guidance(path: Path) -> dict[Move, str]:
    guidance: dict[Move, str] = {}
    current_key: Move | None = None
    current_lines: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        if not raw_line.startswith((" ", "\t")) and raw_line.endswith(":"):
            if current_key is not None:
                guidance[current_key] = " ".join(current_lines).strip()
            current_key = Move(raw_line[:-1])
            current_lines = []
            continue
        if current_key is not None:
            current_lines.append(raw_line.strip())

    if current_key is not None:
        guidance[current_key] = " ".join(current_lines).strip()
    return guidance


def build_behavior_instruction(
    actor: ActorProfile,
    selected_move: Move,
    move_guidance: str,
) -> str:
    return (
        "Meeting Arena behavioural instruction. "
        f"Actor profile: {actor.as_instruction()}. "
        f"Selected move: {selected_move.value}. "
        f"Move guidance: {move_guidance}. "
        "Rendering constraints: normal workplace language; no theatrical roleplay; "
        "no caricature; do not announce personality traits; pressure should often "
        "remain implicit; react to what was actually said; maximum 1-2 short paragraphs."
    )

