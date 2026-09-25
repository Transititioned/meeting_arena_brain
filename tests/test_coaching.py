from pathlib import Path

from arena_brain.coaching import (
    MANAGING_UP_GUIDANCE,
    CoachContext,
    build_coach_context,
    build_coach_prompt,
    get_managing_up_guidance,
)
from arena_brain.engine import load_named_guidance

MANAGING_UP_PRINCIPLES = {
    "ALIGN_BEFORE_CHALLENGE",
    "CLARIFY_PRIORITY",
    "STATE_CONSTRAINT",
    "OFFER_OPTIONS",
    "PROTECT_ACCOUNTABILITY",
    "CONFIRM_AND_RECORD",
}


def test_boss_activates_managing_up_guidance() -> None:
    guidance = get_managing_up_guidance("BOSS")
    assert guidance is not None
    assert guidance == MANAGING_UP_GUIDANCE


def test_peer_does_not_activate_managing_up_guidance() -> None:
    assert get_managing_up_guidance("PEER") is None


def test_direct_report_does_not_activate_managing_up_guidance() -> None:
    assert get_managing_up_guidance("DIRECT_REPORT") is None


def test_missing_relationship_does_not_activate_managing_up_guidance() -> None:
    assert get_managing_up_guidance(None) is None


def test_unknown_relationship_does_not_activate_managing_up_guidance() -> None:
    assert get_managing_up_guidance("STAKEHOLDER") is None


def test_all_six_managing_up_principles_load() -> None:
    guidance = load_named_guidance(Path("config/coach/managing_up.yaml"))
    assert set(guidance) == MANAGING_UP_PRINCIPLES
    for principle in MANAGING_UP_PRINCIPLES:
        assert guidance[principle]


def test_build_coach_context_preserves_latest_utterance_verbatim() -> None:
    messages = [
        {
            "role": "user",
            "content": "[ARENA_ACTOR=priya]   I'm NOT sure   this is Right -- but ok.",
        }
    ]
    context = build_coach_context(messages)
    assert context.latest_user_utterance == "I'm NOT sure   this is Right -- but ok."


def test_build_coach_context_strips_markers_from_context_and_latest() -> None:
    messages = [
        {
            "role": "user",
            "content": "[ARENA_ACTOR=priya] [ARENA_RELATIONSHIP=boss] Are we ready?",
        },
        {"role": "assistant", "content": "We still have two open items."},
        {"role": "user", "content": "[ARENA_ACTOR=priya] So can we call this ready to go?"},
    ]
    context = build_coach_context(messages)
    assert "[ARENA_" not in context.latest_user_utterance
    for message in context.recent_context:
        assert "[ARENA_" not in message["content"]


def test_build_coach_context_excludes_system_messages() -> None:
    messages = [
        {"role": "system", "content": "You are participating in a workplace meeting."},
        {"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"},
    ]
    context = build_coach_context(messages)
    assert all(message["role"] != "system" for message in context.recent_context)
    assert len(context.recent_context) == 1


def test_build_coach_context_caps_recent_context_at_eight_messages() -> None:
    messages = []
    for i in range(12):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"[ARENA_ACTOR=priya] message {i}" if role == "user" else f"message {i}"
        messages.append({"role": role, "content": content})

    context = build_coach_context(messages)
    assert len(context.recent_context) == 8
    assert context.recent_context[0]["content"] == "message 4"
    assert context.recent_context[-1]["content"] == "message 11"


def test_build_coach_context_uses_all_available_when_fewer_than_eight() -> None:
    messages = [
        {"role": "user", "content": "[ARENA_ACTOR=priya] first"},
        {"role": "assistant", "content": "second"},
    ]
    context = build_coach_context(messages)
    assert len(context.recent_context) == 2


def test_build_coach_context_derives_actor_and_relationship() -> None:
    messages = [
        {
            "role": "user",
            "content": "[ARENA_ACTOR=marcus] [ARENA_RELATIONSHIP=peer] What's the evidence?",
        }
    ]
    context = build_coach_context(messages)
    assert context.actor_id == "marcus"
    assert context.relationship_name == "PEER"


def test_build_coach_context_degrades_safely_without_markers() -> None:
    messages = [{"role": "user", "content": "What's the evidence?"}]
    context = build_coach_context(messages)
    assert context.actor_id is None
    assert context.relationship_name is None
    assert context.latest_user_utterance == "What's the evidence?"


def test_build_coach_prompt_includes_managing_up_for_boss() -> None:
    context = CoachContext(
        actor_id="priya",
        relationship_name="BOSS",
        recent_context=[],
        latest_user_utterance="Got it.",
    )
    system_content = build_coach_prompt(context)[0]["content"]
    assert "ALIGN_BEFORE_CHALLENGE" in system_content
    assert "CLARIFY_PRIORITY" in system_content


def test_build_coach_prompt_excludes_managing_up_for_peer() -> None:
    context = CoachContext(
        actor_id="marcus",
        relationship_name="PEER",
        recent_context=[],
        latest_user_utterance="Got it.",
    )
    assert "ALIGN_BEFORE_CHALLENGE" not in build_coach_prompt(context)[0]["content"]


def test_build_coach_prompt_excludes_managing_up_for_direct_report() -> None:
    context = CoachContext(
        actor_id="dana",
        relationship_name="DIRECT_REPORT",
        recent_context=[],
        latest_user_utterance="Got it.",
    )
    assert "ALIGN_BEFORE_CHALLENGE" not in build_coach_prompt(context)[0]["content"]


def test_build_coach_prompt_excludes_managing_up_when_relationship_missing() -> None:
    context = CoachContext(
        actor_id="priya",
        relationship_name=None,
        recent_context=[],
        latest_user_utterance="Got it.",
    )
    assert "ALIGN_BEFORE_CHALLENGE" not in build_coach_prompt(context)[0]["content"]


def test_build_coach_prompt_includes_verbatim_utterance_delimited() -> None:
    context = CoachContext(
        actor_id="priya",
        relationship_name="BOSS",
        recent_context=[],
        latest_user_utterance="Yep, will do.",
    )
    user_content = build_coach_prompt(context)[1]["content"]
    assert "<<<\nYep, will do.\n>>>" in user_content
