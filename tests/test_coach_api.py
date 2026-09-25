import re
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


def test_coach_endpoint_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    response = client.post(
        "/v1/coach",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Yep, will do."}]},
    )
    assert response.status_code == 200
    assert "feedback" in response.json()


def test_boss_relationship_includes_managing_up_repertoire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    response = client.post(
        "/v1/coach",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "[ARENA_ACTOR=priya] [ARENA_RELATIONSHIP=boss] Yep, will do.",
                }
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["relationship"] == "BOSS"
    system_content = captured["calls"][0]["messages"][0]["content"]
    assert "ALIGN_BEFORE_CHALLENGE" in system_content


def test_peer_relationship_excludes_managing_up_repertoire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    response = client.post(
        "/v1/coach",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "[ARENA_ACTOR=marcus] [ARENA_RELATIONSHIP=peer] Yep, will do.",
                }
            ]
        },
    )
    assert response.status_code == 200
    system_content = captured["calls"][0]["messages"][0]["content"]
    assert "ALIGN_BEFORE_CHALLENGE" not in system_content


def test_direct_report_relationship_excludes_managing_up_repertoire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    response = client.post(
        "/v1/coach",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "[ARENA_ACTOR=dana] [ARENA_RELATIONSHIP=direct_report] "
                    "Yep, will do.",
                }
            ]
        },
    )
    assert response.status_code == 200
    system_content = captured["calls"][0]["messages"][0]["content"]
    assert "ALIGN_BEFORE_CHALLENGE" not in system_content


def test_missing_relationship_generic_coach_still_works(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    response = client.post(
        "/v1/coach",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Yep, will do."}]},
    )
    assert response.status_code == 200
    assert response.json()["relationship"] == "none"
    system_content = captured["calls"][0]["messages"][0]["content"]
    assert "ALIGN_BEFORE_CHALLENGE" not in system_content


def test_latest_user_utterance_preserved_verbatim_in_outbound_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    verbatim = "I'm NOT sure   this is Right -- but ok."
    response = client.post(
        "/v1/coach",
        json={"messages": [{"role": "user", "content": f"[ARENA_ACTOR=priya] {verbatim}"}]},
    )
    assert response.status_code == 200
    user_content = captured["calls"][0]["messages"][1]["content"]
    assert verbatim in user_content


def test_machine_control_markers_absent_from_coach_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    response = client.post(
        "/v1/coach",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "[ARENA_ACTOR=priya] [ARENA_RELATIONSHIP=boss] Yep, will do.",
                }
            ]
        },
    )
    assert response.status_code == 200
    for message in captured["calls"][0]["messages"]:
        assert "[ARENA_" not in message["content"]


def test_system_messages_excluded_from_recent_conversation_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    response = client.post(
        "/v1/coach",
        json={
            "messages": [
                {"role": "system", "content": "You are participating in a workplace meeting."},
                {"role": "user", "content": "[ARENA_ACTOR=priya] Yep, will do."},
            ]
        },
    )
    assert response.status_code == 200
    user_content = captured["calls"][0]["messages"][1]["content"]
    assert "workplace meeting" not in user_content


def test_coach_sends_no_more_than_eight_context_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    messages = []
    for i in range(12):
        role = "user" if i % 2 == 0 else "assistant"
        content = f"[ARENA_ACTOR=priya] message {i}" if role == "user" else f"message {i}"
        messages.append({"role": role, "content": content})

    response = client.post("/v1/coach", json={"messages": messages})
    assert response.status_code == 200
    user_content = captured["calls"][0]["messages"][1]["content"]
    recent_section = user_content.split("Recent conversation:")[1].split(
        "User's exact latest response:"
    )[0]
    context_lines = re.findall(r"^(?:user|assistant): ", recent_section, re.MULTILINE)
    assert len(context_lines) <= 8


def test_coach_performs_exactly_one_upstream_call(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    response = client.post(
        "/v1/coach",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Yep, will do."}]},
    )
    assert response.status_code == 200
    assert len(captured["calls"]) == 1


def test_chat_completions_still_performs_exactly_one_call_after_coach_added(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}]},
    )
    assert response.status_code == 200
    assert len(captured["calls"]) == 1


def test_normal_actor_generation_does_not_invoke_coach(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(relationship_name: str | None) -> None:
        raise AssertionError("get_managing_up_guidance must not be called from the actor path")

    monkeypatch.setattr("arena_brain.coaching.get_managing_up_guidance", _boom)

    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    response = client.post(
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
    assert response.status_code == 200


def test_coach_does_not_call_select_move(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(text: str) -> None:
        raise AssertionError("select_move must not be called from the Coach path")

    monkeypatch.setattr("arena_brain.engine.select_move", _boom)

    captured: dict[str, Any] = {}
    monkeypatch.setattr(httpx, "AsyncClient", _make_fake_async_client(captured))

    client = TestClient(app)
    response = client.post(
        "/v1/coach",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Yep, will do."}]},
    )
    assert response.status_code == 200


def test_coach_malformed_messages_returns_clean_400() -> None:
    client = TestClient(app)
    response = client.post("/v1/coach", json={"messages": "not-a-list"})
    assert response.status_code == 400


def test_coach_missing_messages_key_returns_clean_400() -> None:
    client = TestClient(app)
    response = client.post("/v1/coach", json={})
    assert response.status_code == 400


def test_coach_no_usable_user_utterance_returns_clean_400() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/coach",
        json={
            "messages": [
                {"role": "system", "content": "You are in a meeting."},
                {"role": "assistant", "content": "Hello."},
            ]
        },
    )
    assert response.status_code == 400


def test_coach_missing_api_key_returns_clean_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app)
    response = client.post(
        "/v1/coach",
        json={"messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Yep, will do."}]},
    )
    assert response.status_code == 500
