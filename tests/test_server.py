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
                        "[ARENA_ACTOR=priya] [ARENA_STANCE=sceptical] "
                        "[ARENA_CONDITION=pressured] Are we ready?"
                    ),
                }
            ],
        },
    )

    assert response.status_code == 200
    instruction = captured["json"]["messages"][0]["content"]
    assert "Current stance:" in instruction
    assert "Temporary condition:" in instruction
    assert "Actor profile:" not in instruction


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


def test_no_persona_text_injected_for_plain_actor_turn(
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
    instruction = captured["json"]["messages"][0]["content"]
    assert "Actor profile:" not in instruction
    assert "authority=" not in instruction


def test_repeated_move_logs_previous_move_for_verification(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Kev's ask: surface enough in the logs to tell, from real SillyTavern
    traffic, whether the repeated-move check actually fires (i.e. whether
    SillyTavern really resends the actor marker on past turns)."""

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
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(app)
    with caplog.at_level("INFO", logger="arena_brain"):
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
    log_line = caplog.records[-1].message
    assert "previous_move=CLARIFY_BLOCKER" in log_line
    assert "repeated_move=True" in log_line


def test_no_repeat_logs_previous_move_none(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
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
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(app)
    with caplog.at_level("INFO", logger="arena_brain"):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}],
            },
        )

    assert response.status_code == 200
    log_line = caplog.records[-1].message
    assert "previous_move=none" in log_line
    assert "repeated_move=False" in log_line


def test_power_marker_stripped_before_forwarding(monkeypatch: pytest.MonkeyPatch) -> None:
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
                    "content": "[ARENA_ACTOR=priya] [ARENA_POWER=red] Are we ready?",
                }
            ],
        },
    )

    assert response.status_code == 200
    forwarded_messages = captured["json"]["messages"]
    assert all(
        "[ARENA_POWER=" not in (message.get("content") or "")
        for message in forwarded_messages
    )


def test_power_does_not_appear_in_injected_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Iteration-one rule: power difficulty is control metadata only - it
    must never reach the behavioural instruction sent to the LLM."""
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
                    "content": "[ARENA_ACTOR=priya] [ARENA_POWER=red] Are we ready?",
                }
            ],
        },
    )

    assert response.status_code == 200
    instruction = captured["json"]["messages"][0]["content"]
    assert "RED" not in instruction
    assert "power" not in instruction.lower()


def test_power_logged_when_present(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
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
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(app)
    with caplog.at_level("INFO", logger="arena_brain"):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": "[ARENA_ACTOR=priya] [ARENA_POWER=amber] Are we ready?",
                    }
                ],
            },
        )

    assert response.status_code == 200
    log_line = caplog.records[-1].message
    assert "power=AMBER" in log_line


def test_power_logged_as_none_when_absent(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
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
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(app)
    with caplog.at_level("INFO", logger="arena_brain"):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}],
            },
        )

    assert response.status_code == 200
    log_line = caplog.records[-1].message
    assert "power=none" in log_line


def test_power_marker_does_not_change_selected_move(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same user text, only difference is the power marker: selected_move
    must be identical either way."""
    captured: list[dict[str, Any]] = []

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
            captured.append(json)
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(app)
    for power_marker in ("", "[ARENA_POWER=red] "):
        client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": f"[ARENA_ACTOR=priya] {power_marker}Are we ready?",
                    }
                ],
            },
        )

    instructions = [call["messages"][0]["content"] for call in captured]
    assert "Selected move: CLARIFY_BLOCKER" in instructions[0]
    assert "Selected move: CLARIFY_BLOCKER" in instructions[1]


def test_relationship_marker_stripped_before_forwarding(
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
            "messages": [
                {
                    "role": "user",
                    "content": "[ARENA_ACTOR=priya] [ARENA_RELATIONSHIP=boss] Are we ready?",
                }
            ],
        },
    )

    assert response.status_code == 200
    forwarded_messages = captured["json"]["messages"]
    assert all(
        "[ARENA_RELATIONSHIP=" not in (message.get("content") or "")
        for message in forwarded_messages
    )


def test_relationship_does_not_appear_in_injected_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Iteration-one rule: relationship is control metadata only - it must
    never reach the behavioural instruction sent to the LLM."""
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
                    "content": "[ARENA_ACTOR=priya] [ARENA_RELATIONSHIP=boss] Are we ready?",
                }
            ],
        },
    )

    assert response.status_code == 200
    instruction = captured["json"]["messages"][0]["content"]
    assert "BOSS" not in instruction
    assert "relationship" not in instruction.lower()


def test_relationship_logged_when_present(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
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
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(app)
    with caplog.at_level("INFO", logger="arena_brain"):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": "[ARENA_ACTOR=priya] [ARENA_RELATIONSHIP=direct_report] "
                        "Are we ready?",
                    }
                ],
            },
        )

    assert response.status_code == 200
    log_line = caplog.records[-1].message
    assert "relationship=DIRECT_REPORT" in log_line


def test_relationship_logged_as_none_when_absent(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
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
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(app)
    with caplog.at_level("INFO", logger="arena_brain"):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "[ARENA_ACTOR=priya] Are we ready?"}],
            },
        )

    assert response.status_code == 200
    log_line = caplog.records[-1].message
    assert "relationship=none" in log_line


def test_relationship_marker_does_not_change_selected_move(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same user text, only difference is the relationship marker:
    selected_move must be identical either way."""
    captured: list[dict[str, Any]] = []

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
            captured.append(json)
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(app)
    for relationship_marker in ("", "[ARENA_RELATIONSHIP=boss] "):
        client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": f"[ARENA_ACTOR=priya] {relationship_marker}Are we ready?",
                    }
                ],
            },
        )

    instructions = [call["messages"][0]["content"] for call in captured]
    assert "Selected move: CLARIFY_BLOCKER" in instructions[0]
    assert "Selected move: CLARIFY_BLOCKER" in instructions[1]
