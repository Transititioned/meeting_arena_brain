from __future__ import annotations

from pathlib import Path

from arena_brain.engine import load_named_guidance

ROOT = Path(__file__).resolve().parents[1]
MANAGING_UP_GUIDANCE: dict[str, str] = load_named_guidance(
    ROOT / "config" / "coach" / "managing_up.yaml"
)


def get_managing_up_guidance(relationship_name: str | None) -> dict[str, str] | None:
    """Managing Up is a Coach-side evaluation lens, not an actor-generation
    layer: it concerns how the USER communicates with an actor who holds
    formal authority over them, activated only when relationship == BOSS.
    PEER, DIRECT_REPORT, missing, and unknown relationships all resolve to
    None (never an empty dict) - matching how absence is signalled
    elsewhere in this codebase (find_power/find_relationship/
    STANCE_GUIDANCE.get(...)).

    Not consumed anywhere in the current actor-generation path
    (arena_brain/server.py::chat_completions) - this is plumbing for a
    future Coach mode. See SEMANTIC_ARCHITECTURE.md.
    """
    if relationship_name != "BOSS":
        return None
    return MANAGING_UP_GUIDANCE
