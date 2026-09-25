from pathlib import Path

from arena_brain.coaching import MANAGING_UP_GUIDANCE, get_managing_up_guidance
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
