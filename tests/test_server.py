from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from arena_brain.server import app


@pytest.fixture(autouse=True)
def api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")


def test_stream_request_rejected() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "stream": True,
            "messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] hi"}],
        },
    )
    assert response.status_code == 400
    assert "Streaming" in response.json()["detail"]


def test_actor_marker_stripped_before_forwarding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, Any]:
            return {"id": "fake", "choices": []}

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
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(app)
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}],
        },
    )

    assert response.status_code == 200
    forwarded_messages = captured["json"]["messages"]
    assert all(
        "[ARENA_ACTOR=" not in (message.get("content") or "")
        for message in forwarded_messages
    )


def test_stance_and_condition_guidance_forwarded(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, Any]:
            return {"id": "fake", "choices": []}

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
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(app)
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "[ARENA_ACTOR=priya] [ARENA_STANCE=guarded] "
                        "[ARENA_CONDITION=rushed] Are we ready?"
                    ),
                }
            ],
        },
    )

    assert response.status_code == 200
    instruction = captured["json"]["messages"][0]["content"]
    assert "Current stance:" in instruction
    assert "Temporary condition:" in instruction


def test_repeated_move_varies_rendering(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        status_code = 200

        def json(self) -> dict[str, Any]:
            return {"id": "fake", "choices": []}

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
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(app)
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"},
                {"role": "assistant", "content": "We still have two open items."},
                {
                    "role": "user",
                    "content": "[ARENA_ACTOR=priya] Can we call this ready to go?",
                },
            ],
        },
    )

    assert response.status_code == 200
    instruction = captured["json"]["messages"][0]["content"]
    assert "same conversational move" in instruction
