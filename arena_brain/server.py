from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from arena_brain.coach_api import router as coach_router
from arena_brain.engine import (
    build_behavior_instruction,
    find_actor_id,
    find_condition,
    find_power,
    find_relationship,
    find_stance,
    latest_user_text,
    load_move_guidance,
    load_named_guidance,
    previous_move_for_actor,
    select_move,
    strip_actor_markers_from_messages,
)
from arena_brain.settings import get_actor_model, get_coach_model

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
ROOT = Path(__file__).resolve().parents[1]
MOVE_GUIDANCE = load_move_guidance(ROOT / "config" / "moves" / "moves.yaml")
STANCE_GUIDANCE = load_named_guidance(ROOT / "config" / "stances" / "stances.yaml")
CONDITION_GUIDANCE = load_named_guidance(ROOT / "config" / "conditions" / "conditions.yaml")

app = FastAPI(title="Meeting Arena Brain")
logger = logging.getLogger("arena_brain")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app.include_router(coach_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "actor_model": get_actor_model(),
        "coach_model": get_coach_model(),
    }


@app.get("/v1/models")
def models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": get_actor_model(),
                "object": "model",
                "created": 0,
                "owned_by": "openai",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(payload: dict[str, Any]) -> JSONResponse:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set. Supply it locally before calling chat completions.",
        )

    messages = payload.get("messages")
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="messages must be a list")

    if payload.get("stream"):
        raise HTTPException(
            status_code=400,
            detail=(
                "Streaming is not supported by this proxy. "
                "Turn off Streaming in SillyTavern's connection settings."
            ),
        )

    actor_id = find_actor_id(messages)
    user_text = latest_user_text(messages)
    selected_move = select_move(user_text) if actor_id else None
    stance_name = find_stance(messages)
    condition_name = find_condition(messages)
    # Control metadata only in this iteration: logged for visibility, not
    # yet wired into move selection, stance, condition, or rendering.
    # See SEMANTIC_ARCHITECTURE.md.
    power_name = find_power(messages)
    relationship_name = find_relationship(messages)
    previous_move = None
    repeated_move = False
    if actor_id and selected_move:
        previous_move = previous_move_for_actor(messages, actor_id)
        repeated_move = previous_move == selected_move
    clean_messages = strip_actor_markers_from_messages(messages)

    # ARENA_ACTOR_MODEL (default gpt-4o-mini) is authoritative here: any
    # "model" SillyTavern sent in the incoming payload is overwritten, not
    # negotiated with. See SEMANTIC_ARCHITECTURE.md - the Brain, not
    # SillyTavern, owns actor model selection.
    actor_model = get_actor_model()
    outbound = dict(payload)
    outbound["model"] = actor_model
    outbound["messages"] = clean_messages
    if actor_id and selected_move:
        instruction = build_behavior_instruction(
            selected_move=selected_move,
            move_guidance=MOVE_GUIDANCE[selected_move],
            stance_guidance=STANCE_GUIDANCE.get(stance_name) if stance_name else None,
            condition_guidance=CONDITION_GUIDANCE.get(condition_name) if condition_name else None,
            repeated_move=repeated_move,
        )
        outbound["messages"] = [{"role": "system", "content": instruction}, *clean_messages]

    started = time.perf_counter()
    status_code = 0
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OPENAI_CHAT_COMPLETIONS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json=outbound,
            )
        status_code = response.status_code
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "actor=%s power=%s relationship=%s stance=%s condition=%s selected_move=%s "
            "previous_move=%s repeated_move=%s latest_user=%r model=%s http_result=%s "
            "elapsed_ms=%s",
            actor_id or "unknown",
            power_name or "none",
            relationship_name or "none",
            stance_name or "none",
            condition_name or "none",
            selected_move.value if selected_move else "pass_through",
            previous_move.value if previous_move else "none",
            repeated_move,
            user_text[:120],
            actor_model,
            status_code,
            elapsed_ms,
        )
        return JSONResponse(status_code=status_code, content=response.json())
    except httpx.HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "actor=%s power=%s relationship=%s stance=%s condition=%s selected_move=%s "
            "previous_move=%s repeated_move=%s latest_user=%r model=%s http_result=%s "
            "elapsed_ms=%s",
            actor_id or "unknown",
            power_name or "none",
            relationship_name or "none",
            stance_name or "none",
            condition_name or "none",
            selected_move.value if selected_move else "pass_through",
            previous_move.value if previous_move else "none",
            repeated_move,
            user_text[:120],
            actor_model,
            status_code or "transport_error",
            elapsed_ms,
        )
        raise HTTPException(status_code=502, detail="OpenAI request failed") from exc

