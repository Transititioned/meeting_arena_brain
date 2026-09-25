from pathlib import Path

from arena_brain.coaching import (
    MANAGING_UP_GUIDANCE,
    POWER_PROTECTION_GUIDANCE,
    POWER_SENSITIVITY,
    CoachContext,
    build_coach_context,
    build_coach_prompt,
    get_managing_up_guidance,
    get_power_protection_guidance,
    get_power_sensitivity,
)
from arena_brain.engine import load_named_guidance

POWER_PROTECTION_PRINCIPLES = {
    "PROTECT_ROLE_NOT_EGO",
    "TEST_PROCESS_BEFORE_MOTIVE",
    "SURFACE_CONFLICTING_DIRECTIONS",
    "DISTINGUISH_HELP_FROM_TRANSFER",
    "RECLAIM_AUTHORITY_CALMLY",
    "FLAG_ACCOUNTABILITY_WITHOUT_CONTROL",
    "USE_POLITICAL_COVER_SELECTIVELY",
    "PROTECT_CREDIT_NATURALLY",
}

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
        power_name=None,
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
        power_name=None,
        recent_context=[],
        latest_user_utterance="Got it.",
    )
    assert "ALIGN_BEFORE_CHALLENGE" not in build_coach_prompt(context)[0]["content"]


def test_build_coach_prompt_excludes_managing_up_for_direct_report() -> None:
    context = CoachContext(
        actor_id="dana",
        relationship_name="DIRECT_REPORT",
        power_name=None,
        recent_context=[],
        latest_user_utterance="Got it.",
    )
    assert "ALIGN_BEFORE_CHALLENGE" not in build_coach_prompt(context)[0]["content"]


def test_build_coach_prompt_excludes_managing_up_when_relationship_missing() -> None:
    context = CoachContext(
        actor_id="priya",
        relationship_name=None,
        power_name=None,
        recent_context=[],
        latest_user_utterance="Got it.",
    )
    assert "ALIGN_BEFORE_CHALLENGE" not in build_coach_prompt(context)[0]["content"]


def test_build_coach_prompt_includes_verbatim_utterance_delimited() -> None:
    context = CoachContext(
        actor_id="priya",
        relationship_name="BOSS",
        power_name=None,
        recent_context=[],
        latest_user_utterance="Yep, will do.",
    )
    user_content = build_coach_prompt(context)[1]["content"]
    assert "<<<\nYep, will do.\n>>>" in user_content


def test_all_eight_power_protection_principles_load() -> None:
    assert set(POWER_PROTECTION_GUIDANCE) == POWER_PROTECTION_PRINCIPLES
    for principle in POWER_PROTECTION_PRINCIPLES:
        assert POWER_PROTECTION_GUIDANCE[principle]


def test_power_sensitivity_has_all_three_levels() -> None:
    assert set(POWER_SENSITIVITY) == {"GREEN", "AMBER", "RED"}
    for level in ("GREEN", "AMBER", "RED"):
        assert POWER_SENSITIVITY[level]


def test_green_activates_power_protection_guidance() -> None:
    assert get_power_protection_guidance("GREEN") == POWER_PROTECTION_GUIDANCE


def test_amber_activates_power_protection_guidance() -> None:
    assert get_power_protection_guidance("AMBER") == POWER_PROTECTION_GUIDANCE


def test_red_activates_power_protection_guidance() -> None:
    assert get_power_protection_guidance("RED") == POWER_PROTECTION_GUIDANCE


def test_missing_power_does_not_activate_power_protection_guidance() -> None:
    assert get_power_protection_guidance(None) is None


def test_unknown_power_does_not_activate_power_protection_guidance() -> None:
    assert get_power_protection_guidance("BLUE") is None


def test_power_protection_repertoire_is_identical_across_levels() -> None:
    """Power difficulty changes sensitivity, not the underlying evidence
    the Coach draws on - the repertoire itself must not vary by level."""
    assert (
        get_power_protection_guidance("GREEN")
        == get_power_protection_guidance("AMBER")
        == get_power_protection_guidance("RED")
    )


def test_power_sensitivity_differs_by_level() -> None:
    green = get_power_sensitivity("GREEN")
    amber = get_power_sensitivity("AMBER")
    red = get_power_sensitivity("RED")
    assert green != amber != red
    assert len({green, amber, red}) == 3


def test_missing_power_has_no_sensitivity_note() -> None:
    assert get_power_sensitivity(None) is None


def test_unknown_power_has_no_sensitivity_note() -> None:
    assert get_power_sensitivity("BLUE") is None


def test_build_coach_prompt_includes_power_protection_for_red() -> None:
    context = CoachContext(
        actor_id="priya",
        relationship_name=None,
        power_name="RED",
        recent_context=[],
        latest_user_utterance="Got it.",
    )
    system_content = build_coach_prompt(context)[0]["content"]
    assert "PROTECT_ROLE_NOT_EGO" in system_content
    assert "decision rights, accountability, public positioning" in system_content


def test_build_coach_prompt_includes_power_protection_for_green() -> None:
    context = CoachContext(
        actor_id="priya",
        relationship_name=None,
        power_name="GREEN",
        recent_context=[],
        latest_user_utterance="Got it.",
    )
    system_content = build_coach_prompt(context)[0]["content"]
    assert "PROTECT_ROLE_NOT_EGO" in system_content
    assert "Assume normal work-focused hierarchy" in system_content


def test_build_coach_prompt_excludes_power_protection_when_power_missing() -> None:
    context = CoachContext(
        actor_id="priya",
        relationship_name=None,
        power_name=None,
        recent_context=[],
        latest_user_utterance="Got it.",
    )
    system_content = build_coach_prompt(context)[0]["content"]
    assert "PROTECT_ROLE_NOT_EGO" not in system_content
    assert "Power difficulty" not in system_content


def test_build_coach_prompt_power_protection_carries_no_speculation_guardrail() -> None:
    context = CoachContext(
        actor_id="priya",
        relationship_name=None,
        power_name="RED",
        recent_context=[],
        latest_user_utterance="Got it.",
    )
    system_content = build_coach_prompt(context)[0]["content"]
    assert "does not prove motive on its own" in system_content
    assert "supported by what the transcript actually shows" in system_content


def test_build_coach_prompt_includes_both_managing_up_and_power_protection() -> None:
    """The two lenses are orthogonal (BOSS relationship + RED room) and
    must be able to co-occur in the same Coach prompt."""
    context = CoachContext(
        actor_id="priya",
        relationship_name="BOSS",
        power_name="RED",
        recent_context=[],
        latest_user_utterance="Got it.",
    )
    system_content = build_coach_prompt(context)[0]["content"]
    assert "ALIGN_BEFORE_CHALLENGE" in system_content
    assert "PROTECT_ROLE_NOT_EGO" in system_content


def test_build_coach_context_derives_power_name() -> None:
    messages = [
        {
            "role": "user",
            "content": "[ARENA_ACTOR=priya] [ARENA_POWER=amber] Are we ready?",
        }
    ]
    context = build_coach_context(messages)
    assert context.power_name == "AMBER"


def test_build_coach_context_power_name_none_when_absent() -> None:
    messages = [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}]
    context = build_coach_context(messages)
    assert context.power_name is None
