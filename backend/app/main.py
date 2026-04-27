"""FastAPI entrypoint — application bootstrap and middleware.

EN:
    Wires cross-cutting concerns before any route runs:
    - CORS: allows the Next.js dev server (and configured origins) to call
      the API from the browser.
    - Slowapi: per-IP rate limiting to protect the LLM and search backends.
    - Lifespan: opens a shared `httpx.AsyncClient` and connects Redis; on
      shutdown, closes connections cleanly. Also warms the Chroma vector
      store when possible.
    - Routers: `/chat` (Q&A + SSE stream) and `/eval` (benchmark harness).
    - Global exception handler: returns JSON errors instead of raw tracebacks.

    Handlers stay stateless: conversation state lives in Redis via
    `session_store`; the HTTP client and limiter hang off `app.state`.

PT:
    Liga preocupações transversais antes de qualquer rota:
    - CORS: permite ao frontend Next.js (e origens configuradas) chamar a
      API a partir do browser.
    - Slowapi: limite de taxa por IP para proteger o LLM e pesquisas.
    - Lifespan: abre um `httpx.AsyncClient` partilhado e liga o Redis; no
      encerramento fecha ligações. Aquece o vector store Chroma quando possível.
    - Routers: `/chat` (Q&A + stream SSE) e `/eval` (harness de benchmark).
    - Handler global de exceções: devolve JSON em vez de tracebacks crus.

    Os handlers permanecem sem estado: o estado da conversa está no Redis;
    o cliente HTTP e o limiter ficam em `app.state`.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import chat as chat_routes
from app.api.routes import eval as eval_routes
from app.config import settings
from app.logging_config import logger
from app.retrieval.vector_store import vector_store
from app.session_store import session_store


# EN: Default 120 requests/minute per IP — tune via Slowapi if needed.
# PT: Limite por defeito de 120 pedidos/minuto por IP — ajustável no Slowapi.
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # EN: Startup: pooled HTTP client for Tavily, DRE fetches, etc. One client
    #     per process avoids connection churn under load.
    # PT: Arranque: cliente HTTP em pool para Tavily, DRE, etc. Um cliente por
    #     processo evita abrir/fechar ligações sob carga.
    logger.info("Starting HomoDeus Labor Agent v{}", settings.agent_version)
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(20.0, connect=5.0),
        limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
        headers={"User-Agent": "HomoDeus-LaborAgent/1.0 (+research)"},
        follow_redirects=True,
    )
    await session_store.connect()
    try:
        # EN: Labor Code embeddings live on disk; failure here still allows chat
        #     if tools degrade (e.g. web-only).
        # PT: Embeddings do CT em disco; falha aqui ainda permite chat se as
        #     ferramentas degradarem (ex.: só web).
        vector_store.ensure_initialized()
    except Exception as exc:  # pragma: no cover
        logger.warning("Vector store init failed (continuing): {}", exc)
    yield
    await app.state.http_client.aclose()
    await session_store.disconnect()
    logger.info("Shutdown complete")


app = FastAPI(
    title="HomoDeus Labor Law Q&A Agent",
    description=(
        "Production-grade conversational agent for Portuguese labor law and "
        "payroll. Tool-calling architecture with hybrid retrieval (vector "
        "index + live web search) and deterministic salary calculators."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
# EN: Slowapi needs the limiter on app.state for decorators on routes.
# PT: O Slowapi precisa do limiter em app.state para decoradores nas rotas.
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on {}: {}", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": str(exc)},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "agent_version": settings.agent_version}


app.include_router(chat_routes.router, prefix="/chat", tags=["chat"])
app.include_router(eval_routes.router, prefix="/eval", tags=["eval"])
