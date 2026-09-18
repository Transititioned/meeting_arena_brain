from pathlib import Path

from arena_brain.actors import get_actor
from arena_brain.engine import (
    Move,
    find_actor_id,
    latest_user_text,
    load_move_guidance,
    select_move,
    strip_actor_markers_from_messages,
)


def test_clarify_blocker() -> None:
    assert select_move("I'm not convinced we're ready for SIT") == Move.CLARIFY_BLOCKER


def test_surface_tradeoff() -> None:
    assert select_move("If we do that, reporting slips a week") == Move.SURFACE_TRADEOFF


def test_protect_accountability() -> None:
    assert select_move("That wasn't what we agreed") == Move.PROTECT_ACCOUNTABILITY


def test_acknowledge_then_reframe() -> None:
    assert (
        select_move("I understand the point, but I don't agree")
        == Move.ACKNOWLEDGE_THEN_REFRAME
    )


def test_ask_for_specifics() -> None:
    assert select_move("Can you explain what you mean?") == Move.ASK_FOR_SPECIFICS


def test_clarify_blocker_wins_over_but() -> None:
    text = (
        "I'm comfortable starting SIT, but I don't think we should call the "
        "environment issues resolved yet."
    )
    assert select_move(text) == Move.CLARIFY_BLOCKER


def test_actor_marker_parsing() -> None:
    messages = [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}]
    assert find_actor_id(messages) == "priya"
    assert get_actor(find_actor_id(messages)).role == "Service Owner"
    assert latest_user_text(messages) == "Are we ready?"


def test_unknown_actor_degrades_safely() -> None:
    messages = [{"role": "user", "content": "[ARENA_ACTOR=unknown] Are we ready?"}]
    assert find_actor_id(messages) is None
    assert get_actor(find_actor_id(messages)) is None


def test_strip_actor_markers_from_messages() -> None:
    messages = [
        {"role": "system", "content": "unrelated"},
        {"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"},
    ]
    cleaned = strip_actor_markers_from_messages(messages)
    assert cleaned[1]["content"] == "Are we ready?"
    assert "[ARENA_ACTOR=" not in cleaned[0]["content"]
    assert messages[1]["content"] == "[ARENA_ACTOR=priya] Are we ready?"


def test_move_guidance_loads() -> None:
    guidance = load_move_guidance(Path("config/moves/moves.yaml"))
    assert "prevents progress" in guidance[Move.CLARIFY_BLOCKER]

