from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from arena_brain.actors import get_actor
from arena_brain.engine import (
    build_behavior_instruction,
    find_actor_id,
    latest_user_text,
    load_move_guidance,
    select_move,
)


OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"
ROOT = Path(__file__).resolve().parents[1]
MOVE_GUIDANCE = load_move_guidance(ROOT / "config" / "moves" / "moves.yaml")

app = FastAPI(title="Meeting Arena Brain")
logger = logging.getLogger("arena_brain")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
def models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL,
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

    actor_id = find_actor_id(messages)
    actor = get_actor(actor_id)
    user_text = latest_user_text(messages)
    selected_move = select_move(user_text) if actor else None

    outbound = dict(payload)
    outbound["model"] = MODEL
    if actor and selected_move:
        instruction = build_behavior_instruction(
            actor=actor,
            selected_move=selected_move,
            move_guidance=MOVE_GUIDANCE[selected_move],
        )
        outbound["messages"] = [{"role": "system", "content": instruction}, *messages]

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
            "actor=%s selected_move=%s latest_user=%r model=%s http_result=%s elapsed_ms=%s",
            actor_id or "unknown",
            selected_move.value if selected_move else "pass_through",
            user_text[:120],
            MODEL,
            status_code,
            elapsed_ms,
        )
        return JSONResponse(status_code=status_code, content=response.json())
    except httpx.HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "actor=%s selected_move=%s latest_user=%r model=%s http_result=%s elapsed_ms=%s",
            actor_id or "unknown",
            selected_move.value if selected_move else "pass_through",
            user_text[:120],
            MODEL,
            status_code or "transport_error",
            elapsed_ms,
        )
        raise HTTPException(status_code=502, detail="OpenAI request failed") from exc

