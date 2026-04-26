"""Chat HTTP routes.

- POST /chat: full request/response (no streaming) — used by tests and the
  evaluation harness. Returns the full AgentState as JSON.
- GET  /chat/stream: SSE stream of agent events. The frontend opens this and
  renders each event as it arrives (phase markers, tool calls, sources,
  tokens, confidence, refusal, done).
- GET  /chat/conversations: list active conversation ids.
- GET  /chat/conversations/{id}: fetch a conversation's history.
- DELETE /chat/conversations/{id}: clear a conversation.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.graph import LaborAgent
from app.config import settings
from app.logging_config import logger
from app.session_store import session_store


router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str | None = None
    agent_version: str | None = None  # "v1" | "v2"


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    confidence: float
    refused: bool
    sources: list[dict[str, Any]]
    tool_traces: list[dict[str, Any]]
    iterations: int
    agent_version: str


def _agent_for(request: Request, version: str | None) -> LaborAgent:
    return LaborAgent(http_client=request.app.state.http_client, version=version)


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    if not settings.active_api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                f"LLM provider '{settings.llm_provider}' is not configured. "
                "Set GROQ_API_KEY (or switch LLM_PROVIDER=openai and set OPENAI_API_KEY)."
            ),
        )

    conv_id = req.conversation_id or str(uuid.uuid4())
    history = await session_store.get(conv_id)

    agent = _agent_for(request, req.agent_version)
    state = await agent.run(req.message, history=history, conversation_id=conv_id)

    await session_store.append(conv_id, {"role": "user", "content": req.message})
    await session_store.append(
        conv_id,
        {
            "role": "assistant",
            "content": state.get("final_answer", ""),
            "metadata": {
                "confidence": state.get("confidence", 0.0),
                "refused": state.get("refused", False),
                "sources": [s.model_dump() if hasattr(s, "model_dump") else s for s in state.get("sources", [])],
            },
        },
    )

    return ChatResponse(
        conversation_id=conv_id,
        answer=state.get("final_answer", ""),
        confidence=float(state.get("confidence", 0.0)),
        refused=bool(state.get("refused", False)),
        sources=[s.model_dump() if hasattr(s, "model_dump") else s for s in state.get("sources", [])],
        tool_traces=[t.model_dump() if hasattr(t, "model_dump") else t for t in state.get("tool_traces", [])],
        iterations=int(state.get("iterations", 0)),
        agent_version=str(state.get("agent_version", "v2")),
    )


@router.get("/stream")
async def chat_stream(
    request: Request,
    message: str = Query(..., min_length=1, max_length=4000),
    conversation_id: str | None = Query(default=None),
    agent_version: str | None = Query(default=None),
) -> StreamingResponse:
    if not settings.active_api_key:
        raise HTTPException(
            status_code=500,
            detail=(
                f"LLM provider '{settings.llm_provider}' is not configured. "
                "Set GROQ_API_KEY (or switch LLM_PROVIDER=openai and set OPENAI_API_KEY)."
            ),
        )

    conv_id = conversation_id or str(uuid.uuid4())
    history = await session_store.get(conv_id)
    agent = _agent_for(request, agent_version)

    async def generator() -> AsyncIterator[bytes]:
        yield _sse({"type": "start", "conversation_id": conv_id, "agent_version": agent.version})
        final_answer = ""
        try:
            async for event in agent.stream(message, history=history, conversation_id=conv_id):
                if await request.is_disconnected():
                    logger.info("Client disconnected from stream {}", conv_id)
                    break
                if event.get("type") == "done":
                    final_answer = event["state"].get("final_answer", "")
                yield _sse(event)
        except asyncio.CancelledError:
            logger.info("Stream cancelled: {}", conv_id)
            raise
        except Exception as exc:
            logger.exception("Stream error: {}", exc)
            yield _sse({"type": "error", "message": str(exc)})

        try:
            await session_store.append(conv_id, {"role": "user", "content": message})
            await session_store.append(
                conv_id, {"role": "assistant", "content": final_answer}
            )
        except Exception as exc:
            logger.warning("Could not persist conversation {}: {}", conv_id, exc)

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(generator(), media_type="text/event-stream", headers=headers)


def _sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


@router.get("/conversations")
async def list_conversations() -> dict[str, list[str]]:
    return {"ids": await session_store.list_ids()}


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str) -> dict[str, Any]:
    history = await session_store.get(conv_id)
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation_id": conv_id, "messages": history}


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str) -> dict[str, str]:
    await session_store.delete(conv_id)
    return {"status": "deleted", "conversation_id": conv_id}
