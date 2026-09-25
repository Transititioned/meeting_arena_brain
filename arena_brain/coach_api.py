from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from arena_brain.coaching import build_coach_context, build_coach_prompt

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"

router = APIRouter()
logger = logging.getLogger("arena_brain")


@router.post("/v1/coach")
async def coach(payload: dict[str, Any]) -> JSONResponse:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set. Supply it locally before calling Coach.",
        )

    messages = payload.get("messages")
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="messages must be a list")

    context = build_coach_context(messages)
    if not context.latest_user_utterance:
        raise HTTPException(
            status_code=400,
            detail="No usable latest user utterance found in messages.",
        )

    coach_messages = build_coach_prompt(context)

    started = time.perf_counter()
    status_code = 0
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OPENAI_CHAT_COMPLETIONS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": MODEL, "messages": coach_messages},
            )
        status_code = response.status_code
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        body = response.json()
        feedback = body["choices"][0]["message"]["content"]
        logger.info(
            "coach actor=%s relationship=%s http_result=%s elapsed_ms=%s",
            context.actor_id or "unknown",
            context.relationship_name or "none",
            status_code,
            elapsed_ms,
        )
        return JSONResponse(
            status_code=status_code,
            content={
                "feedback": feedback,
                "relationship": context.relationship_name or "none",
                "actor": context.actor_id or "unknown",
            },
        )
    except httpx.HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "coach actor=%s relationship=%s http_result=%s elapsed_ms=%s",
            context.actor_id or "unknown",
            context.relationship_name or "none",
            status_code or "transport_error",
            elapsed_ms,
        )
        raise HTTPException(status_code=502, detail="OpenAI request failed") from exc
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenAI response was not in the expected shape",
        ) from exc
