import pytest

from arena_brain.settings import (
    DEFAULT_ACTOR_MODEL,
    DEFAULT_COACH_MODEL,
    get_actor_model,
    get_coach_model,
)


@pytest.fixture(autouse=True)
def clean_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARENA_ACTOR_MODEL", raising=False)
    monkeypatch.delenv("ARENA_COACH_MODEL", raising=False)


def test_defaults_are_gpt_4o_mini() -> None:
    assert DEFAULT_ACTOR_MODEL == "gpt-4o-mini"
    assert DEFAULT_COACH_MODEL == "gpt-4o-mini"


def test_both_models_default_when_env_vars_missing() -> None:
    assert get_actor_model() == "gpt-4o-mini"
    assert get_coach_model() == "gpt-4o-mini"


def test_actor_model_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARENA_ACTOR_MODEL", "gpt-4.1-mini")
    assert get_actor_model() == "gpt-4.1-mini"


def test_coach_model_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARENA_COACH_MODEL", "gpt-4.1")
    assert get_coach_model() == "gpt-4.1"


def test_models_are_independent_when_both_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARENA_ACTOR_MODEL", "actor-candidate-model")
    monkeypatch.setenv("ARENA_COACH_MODEL", "coach-candidate-model")
    assert get_actor_model() == "actor-candidate-model"
    assert get_coach_model() == "coach-candidate-model"


def test_blank_env_value_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARENA_ACTOR_MODEL", "")
    monkeypatch.setenv("ARENA_COACH_MODEL", "")
    assert get_actor_model() == "gpt-4o-mini"
    assert get_coach_model() == "gpt-4o-mini"


def test_whitespace_only_env_value_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARENA_ACTOR_MODEL", "   ")
    assert get_actor_model() == "gpt-4o-mini"


def test_whitespace_is_stripped_from_valid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARENA_ACTOR_MODEL", "  gpt-4.1-mini  ")
    assert get_actor_model() == "gpt-4.1-mini"


def test_arbitrary_model_identifiers_are_allowed_without_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARENA_COACH_MODEL", "some-not-yet-released-model-id")
    assert get_coach_model() == "some-not-yet-released-model-id"
