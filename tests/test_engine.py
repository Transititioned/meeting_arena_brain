from pathlib import Path

from arena_brain.actors import get_actor
from arena_brain.engine import (
    Move,
    find_actor_id,
    find_condition,
    find_stance,
    latest_user_text,
    load_move_guidance,
    load_named_guidance,
    previous_move_for_actor,
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


def test_stance_and_condition_marker_parsing() -> None:
    messages = [
        {
            "role": "user",
            "content": "[ARENA_ACTOR=priya] [ARENA_STANCE=sceptical] [ARENA_CONDITION=pressured] Are we ready?",
        }
    ]
    assert find_stance(messages) == "SCEPTICAL"
    assert find_condition(messages) == "PRESSURED"


def test_missing_stance_and_condition_markers_return_none() -> None:
    messages = [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}]
    assert find_stance(messages) is None
    assert find_condition(messages) is None


def test_strip_actor_markers_from_messages_also_strips_stance_and_condition() -> None:
    messages = [
        {
            "role": "user",
            "content": "[ARENA_ACTOR=priya] [ARENA_STANCE=sceptical] [ARENA_CONDITION=pressured] Are we ready?",
        }
    ]
    cleaned = strip_actor_markers_from_messages(messages)
    assert cleaned[0]["content"] == "Are we ready?"


def test_named_guidance_loads() -> None:
    guidance = load_named_guidance(Path("config/stances/stances.yaml"))
    assert "measured" in guidance["SCEPTICAL"]


def test_previous_move_for_actor_none_on_first_turn() -> None:
    messages = [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}]
    assert previous_move_for_actor(messages, "priya") is None


def test_previous_move_for_actor_recomputes_deterministically() -> None:
    messages = [
        {"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"},
        {"role": "assistant", "content": "We still have two open items."},
        {"role": "user", "content": "[ARENA_ACTOR=priya] Can you explain what you mean?"},
    ]
    assert previous_move_for_actor(messages, "priya") == Move.CLARIFY_BLOCKER


def test_previous_move_for_actor_ignores_other_actors() -> None:
    messages = [
        {"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"},
        {"role": "user", "content": "[ARENA_ACTOR=marcus] What's the evidence?"},
    ]
    assert previous_move_for_actor(messages, "priya") is None


def test_previous_move_for_actor_in_a_realistic_group_chat_history() -> None:
    """Shaped like a real multi-turn SillyTavern group chat: a system prompt,
    several actors interleaved, and assistant replies in between. This only
    passes if SillyTavern actually resends the actor marker on every past
    turn, not just the newest one — the assumption the repeated-move feature
    depends on.
    """
    messages = [
        {"role": "system", "content": "You are participating in a workplace meeting."},
        {"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready to start SIT?"},
        {"role": "assistant", "content": "We still have two environment issues open."},
        {"role": "user", "content": "[ARENA_ACTOR=marcus] What's the evidence those block us?"},
        {"role": "assistant", "content": "Here's the test log from yesterday."},
        {"role": "user", "content": "[ARENA_ACTOR=dana] The integration owner hasn't signed off."},
        {"role": "assistant", "content": "I'll chase that this afternoon."},
        {"role": "user", "content": "[ARENA_ACTOR=priya] So can we call this ready to go?"},
    ]
    assert previous_move_for_actor(messages, "priya") == Move.CLARIFY_BLOCKER
    assert previous_move_for_actor(messages, "marcus") is None
    assert previous_move_for_actor(messages, "dana") is None


def test_previous_move_for_actor_degrades_safely_when_history_lacks_markers() -> None:
    """If SillyTavern does NOT resend the marker on past turns (only the
    newest message carries it), the feature must degrade to "no repeat
    detected" rather than raising or misattributing a turn.
    """
    messages = [
        {"role": "user", "content": "Are we ready to start SIT?"},
        {"role": "assistant", "content": "We still have two environment issues open."},
        {"role": "user", "content": "[ARENA_ACTOR=priya] So can we call this ready to go?"},
    ]
    assert previous_move_for_actor(messages, "priya") is None

