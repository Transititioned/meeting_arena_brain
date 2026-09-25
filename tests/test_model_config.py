from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from arena_brain.server import app


@pytest.fixture(autouse=True)
def api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.delenv("ARENA_ACTOR_MODEL", raising=False)
    monkeypatch.delenv("ARENA_COACH_MODEL", raising=False)


def _make_fake_async_client(captured: dict[str, Any], feedback: str = "Looks good.") -> type:
    captured.setdefault("calls", [])

    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, Any]:
            return {"id": "fake", "choices": [{"message": {"content": feedback}}]}

    class FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def post(
            self, url: str, headers: dict[str, str], json: dict[str, Any]
        ) -> FakeResponse:
            captured["calls"].append(json)
            return FakeResponse()

    return FakeAsyncClient


# ---------------------------------------------------------------------------
# Model routing
# ---------------------------------------------------------------------------


def test_actor_request_uses_default_model_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}]},
    )
    assert captured["calls"][0]["model"] == "gpt-4o-mini"


def test_coach_request_uses_default_model_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    client.post(
        "/v1/coach",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Yep, will do."}]},
    )
    assert captured["calls"][0]["model"] == "gpt-4o-mini"


def test_arena_actor_model_env_var_overrides_actor_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARENA_ACTOR_MODEL", "actor-candidate-model")
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}]},
    )
    assert captured["calls"][0]["model"] == "actor-candidate-model"


def test_arena_coach_model_env_var_overrides_coach_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARENA_COACH_MODEL", "coach-candidate-model")
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    client.post(
        "/v1/coach",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Yep, will do."}]},
    )
    assert captured["calls"][0]["model"] == "coach-candidate-model"


def test_actor_and_coach_models_differ_simultaneously(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARENA_ACTOR_MODEL", "actor-candidate-model")
    monkeypatch.setenv("ARENA_COACH_MODEL", "coach-candidate-model")
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}]},
    )
    client.post(
        "/v1/coach",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Yep, will do."}]},
    )
    assert captured["calls"][0]["model"] == "actor-candidate-model"
    assert captured["calls"][1]["model"] == "coach-candidate-model"


def test_blank_actor_model_env_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARENA_ACTOR_MODEL", "   ")
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}]},
    )
    assert captured["calls"][0]["model"] == "gpt-4o-mini"


def test_incoming_payload_model_does_not_override_actor_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARENA_ACTOR_MODEL", "actor-candidate-model")
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    client.post(
        "/v1/chat/completions",
        json={
            "model": "whatever-sillytavern-sent",
            "messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}],
        },
    )
    assert captured["calls"][0]["model"] == "actor-candidate-model"


def test_incoming_payload_model_does_not_affect_coach_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARENA_COACH_MODEL", "coach-candidate-model")
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    client.post(
        "/v1/coach",
        json={
            "model": "whatever-was-sent",
            "messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Yep, will do."}],
        },
    )
    assert captured["calls"][0]["model"] == "coach-candidate-model"


def test_v1_models_reports_configured_actor_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARENA_ACTOR_MODEL", "actor-candidate-model")
    client = TestClient(app)
    response = client.get("/v1/models")
    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "actor-candidate-model"


def test_health_reports_both_configured_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARENA_ACTOR_MODEL", "actor-candidate-model")
    monkeypatch.setenv("ARENA_COACH_MODEL", "coach-candidate-model")
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["actor_model"] == "actor-candidate-model"
    assert body["coach_model"] == "coach-candidate-model"


def test_actor_logging_reports_actor_model(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("ARENA_ACTOR_MODEL", "actor-candidate-model")
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    with caplog.at_level("INFO", logger="arena_brain"):
        client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}]
            },
        )
    log_line = caplog.records[-1].message
    assert "model=actor-candidate-model" in log_line


def test_coach_logging_reports_coach_model(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("ARENA_COACH_MODEL", "coach-candidate-model")
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    with caplog.at_level("INFO", logger="arena_brain"):
        client.post(
            "/v1/coach",
            json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Yep, will do."}]},
        )
    log_line = caplog.records[-1].message
    assert "model=coach-candidate-model" in log_line


# ---------------------------------------------------------------------------
# Behaviour-lane compartmentalisation
# ---------------------------------------------------------------------------


def test_actor_instruction_never_contains_coach_material(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    client.post(
        "/v1/chat/completions",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "[ARENA_ACTOR=priya] [ARENA_RELATIONSHIP=boss] Are we ready?",
                }
            ]
        },
    )
    instruction = captured["calls"][0]["messages"][0]["content"]
    for forbidden in (
        "Meeting Arena Coach",
        "ALIGN_BEFORE_CHALLENGE",
        "CLARIFY_PRIORITY",
        "STATE_CONSTRAINT",
        "OFFER_OPTIONS",
        "PROTECT_ACCOUNTABILITY",
        "CONFIRM_AND_RECORD",
    ):
        assert forbidden not in instruction


def test_coach_prompt_never_contains_actor_rendering_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    client.post(
        "/v1/coach",
        json={
            "messages": [
                {"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"},
                {"role": "assistant", "content": "We still have two open items."},
                {
                    "role": "user",
                    "content": "[ARENA_ACTOR=priya] [ARENA_STANCE=sceptical] "
                    "[ARENA_CONDITION=frazzled] Can we call this ready to go?",
                },
            ]
        },
    )
    for message in captured["calls"][0]["messages"]:
        content = message["content"]
        for forbidden in (
            "Selected move:",
            "Move guidance:",
            "Current stance:",
            "Temporary condition:",
            "same conversational move",
        ):
            assert forbidden not in content
