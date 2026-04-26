"""FastAPI entrypoint.

Wires:
- CORS for the Next.js frontend
- Slowapi rate limiting (per IP)
- Redis session store lifecycle
- Chat + Eval routers
- Health endpoint

Designed to scale: stateless handlers, async everywhere, connection-pooled
HTTP and Redis clients reused across requests via app.state.
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


limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting HomoDeus Labor Agent v{}", settings.agent_version)
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(20.0, connect=5.0),
        limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
        headers={"User-Agent": "HomoDeus-LaborAgent/1.0 (+research)"},
        follow_redirects=True,
    )
    await session_store.connect()
    try:
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
