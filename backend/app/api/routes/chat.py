"""Chat HTTP routes — non-streaming JSON and SSE streaming.

EN:
    - POST `/chat`: waits for the full agent run, returns one JSON payload
      (answer, sources, traces, confidence). Used by integration tests and
      scripts; simpler than parsing SSE.
    - GET `/chat/stream`: Server-Sent Events. Each line is `data: {json}\\n\\n`.
      Event types include `phase`, `tool_call`, `sources`, `token`, `confidence`,
      `refusal`, `done`. The frontend consumes this for live UX.
    - Conversation CRUD: list ids, fetch history, delete. History is stored
      via `session_store` (Redis or memory fallback).

    Locale: `locale` query/body selects `pt` vs `en` for the agent's reply
    language (legal citations stay in Portuguese per prompt rules).

PT:
    - POST `/chat`: espera o agente terminar e devolve um JSON completo.
      Usado em testes de integração; mais simples do que parsear SSE.
    - GET `/chat/stream`: Server-Sent Events. Cada evento é JSON com `type`.
      Tipos: `phase`, `tool_call`, `sources`, `token`, `confidence`, etc.
    - CRUD de conversas: listar ids, obter histórico, apagar. O histórico vai
      para `session_store` (Redis ou memória).

    Locale: parâmetro `locale` escolhe `pt` vs `en` para o idioma da resposta
    (citações legais mantêm-se em português conforme o prompt).
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
    # EN: `conversation_id` optional — server creates UUID on first message.
    # PT: `conversation_id` opcional — o servidor cria UUID na primeira mensagem.
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str | None = None
    agent_version: str | None = None  # "v1" | "v2"
    locale: str | None = None  # "pt" | "en"


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    confidence: float
    refused: bool
    sources: list[dict[str, Any]]
    tool_traces: list[dict[str, Any]]
    iterations: int
    agent_version: str


def _normalize_locale(value: str | None) -> str:
    # EN: Only `en` is special-cased; everything else maps to Portuguese.
    # PT: Só `en` é tratado à parte; todo o resto mapeia para português.
    v = (value or "pt").strip().lower()
    return "en" if v == "en" else "pt"


def _agent_for(
    request: Request, version: str | None, locale: str | None = None
) -> LaborAgent:
    return LaborAgent(
        http_client=request.app.state.http_client,
        version=version,
        locale=_normalize_locale(locale),
    )


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    # EN: Fail fast if no LLM key — avoids opaque errors deep inside the agent.
    # PT: Falha cedo sem chave LLM — evita erros opacos dentro do agente.
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

    agent = _agent_for(request, req.agent_version, req.locale)
    # EN: `run()` drains the async generator until `done` — same logic as stream.
    # PT: `run()` consome o gerador async até `done` — mesma lógica que o stream.
    state = await agent.run(req.message, history=history, conversation_id=conv_id)

    # EN: Persist user + assistant turns; metadata holds structured fields for UI.
    # PT: Grava turnos user + assistant; metadata com campos estruturados para a UI.
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
    locale: str | None = Query(default=None),
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
    agent = _agent_for(request, agent_version, locale)

    async def generator() -> AsyncIterator[bytes]:
        # EN: First event tells the client which conversation id to reuse on follow-ups.
        # PT: Primeiro evento indica ao cliente qual `conversation_id` reutilizar.
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
    # EN: SSE framing: each event is one line starting with `data: `, blank line ends event.
    # PT: Formato SSE: cada evento é uma linha `data: `, linha em branco fecha o evento.
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
