from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from arena_brain.server import app


@pytest.fixture(autouse=True)
def api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")


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


def _coach_request(client: TestClient, content: str) -> dict[str, Any]:
    response = client.post(
        "/v1/coach",
        json={"messages": [{"role": "user", "content": content}]},
    )
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize("level", ["green", "amber", "red"])
def test_each_power_level_includes_power_protection_in_coach_prompt(
    level: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    _coach_request(
        client, f"[ARENA_ACTOR=priya] [ARENA_POWER={level}] Are we ready?"
    )
    system_content = captured["calls"][0]["messages"][0]["content"]
    assert "PROTECT_ROLE_NOT_EGO" in system_content


def test_missing_power_excludes_power_protection_from_coach_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    _coach_request(client, "[ARENA_ACTOR=priya] Are we ready?")
    system_content = captured["calls"][0]["messages"][0]["content"]
    assert "PROTECT_ROLE_NOT_EGO" not in system_content


def test_unknown_power_value_excludes_power_protection_from_coach_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    _coach_request(client, "[ARENA_ACTOR=priya] [ARENA_POWER=blue] Are we ready?")
    system_content = captured["calls"][0]["messages"][0]["content"]
    assert "PROTECT_ROLE_NOT_EGO" not in system_content


def test_power_marker_stripped_from_coach_outbound_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    _coach_request(client, "[ARENA_ACTOR=priya] [ARENA_POWER=red] Are we ready?")
    for message in captured["calls"][0]["messages"]:
        assert "[ARENA_POWER=" not in message["content"]


def test_coach_response_includes_power_field(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    body = _coach_request(client, "[ARENA_ACTOR=priya] [ARENA_POWER=amber] Are we ready?")
    assert body["power"] == "AMBER"


def test_coach_response_reports_power_none_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    body = _coach_request(client, "[ARENA_ACTOR=priya] Are we ready?")
    assert body["power"] == "none"


def test_coach_logging_reports_power(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    with caplog.at_level("INFO", logger="arena_brain"):
        _coach_request(client, "[ARENA_ACTOR=priya] [ARENA_POWER=red] Are we ready?")
    log_line = caplog.records[-1].message
    assert "power=RED" in log_line


def test_managing_up_and_power_protection_combine_in_one_coach_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    _coach_request(
        client,
        "[ARENA_ACTOR=priya] [ARENA_RELATIONSHIP=boss] [ARENA_POWER=red] "
        "Are we ready?",
    )
    system_content = captured["calls"][0]["messages"][0]["content"]
    assert "ALIGN_BEFORE_CHALLENGE" in system_content
    assert "PROTECT_ROLE_NOT_EGO" in system_content


def test_power_protection_never_appears_in_actor_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Power Protection is a Coach-only lens - it must never leak into the
    actor-generation prompt, however the room's power difficulty is set."""
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    client.post(
        "/v1/chat/completions",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "[ARENA_ACTOR=priya] [ARENA_POWER=red] Are we ready?",
                }
            ]
        },
    )
    instruction = captured["calls"][0]["messages"][0]["content"]
    for forbidden in (
        "PROTECT_ROLE_NOT_EGO",
        "TEST_PROCESS_BEFORE_MOTIVE",
        "SURFACE_CONFLICTING_DIRECTIONS",
        "DISTINGUISH_HELP_FROM_TRANSFER",
        "RECLAIM_AUTHORITY_CALMLY",
        "FLAG_ACCOUNTABILITY_WITHOUT_CONTROL",
        "USE_POLITICAL_COVER_SELECTIVELY",
        "PROTECT_CREDIT_NATURALLY",
    ):
        assert forbidden not in instruction
