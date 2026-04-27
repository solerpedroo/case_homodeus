"""Redis-backed conversation store.

EN:
    FastAPI handlers do not hold conversation state in memory. Each turn loads
    history by `conversation_id` from Redis (JSON list of messages), appends the
    new user/assistant messages, and sets a TTL so old threads expire.

    If `connect()` cannot reach Redis, `_fallback` switches to an in-process
    dict. That is enough for local dev without Docker, but data is lost on
    restart and is not shared across workers.

PT:
    Os handlers FastAPI não guardam estado da conversa em memória. Cada turno
    carrega o histórico por `conversation_id` a partir do Redis (lista JSON),
    acrescenta mensagens user/assistant e define TTL para expirar threads antigas.

    Se `connect()` não alcançar o Redis, `_fallback` usa um dicionário em
    processo. Serve para desenvolvimento local sem Docker, mas os dados
    perdem-se ao reiniciar e não são partilhados entre workers.
"""
from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from app.config import settings
from app.logging_config import logger

# EN: Key namespace avoids collisions with other apps on shared Redis.
# PT: Espaço de nomes de chaves evita colisões com outras apps no mesmo Redis.
_KEY_PREFIX = "homodeus:conv:"
_INDEX_KEY = "homodeus:conv:index"


class SessionStore:
    def __init__(self) -> None:
        # EN: `_memory` + `_memory_index` mirror Redis behaviour when offline.
        # PT: `_memory` + `_memory_index` espelham o Redis quando está offline.
        self._redis: redis.Redis | None = None
        self._memory: dict[str, list[dict[str, Any]]] = {}
        self._memory_index: list[str] = []
        self._fallback = False

    async def connect(self) -> None:
        try:
            self._redis = redis.from_url(
                settings.redis_url, encoding="utf-8", decode_responses=True
            )
            await self._redis.ping()
            logger.info("Redis connected at {}", settings.redis_url)
        except Exception as exc:  # pragma: no cover - depends on env
            logger.warning("Redis unavailable, using in-memory fallback: {}", exc)
            self._fallback = True
            self._redis = None

    async def disconnect(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()

    async def get(self, conv_id: str) -> list[dict[str, Any]]:
        if self._fallback or self._redis is None:
            return list(self._memory.get(conv_id, []))
        raw = await self._redis.get(_KEY_PREFIX + conv_id)
        if raw is None:
            return []
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Corrupt conversation in Redis: {}", conv_id)
            return []

    async def append(self, conv_id: str, message: dict[str, Any]) -> None:
        history = await self.get(conv_id)
        history.append(message)
        await self.set(conv_id, history)

    async def set(self, conv_id: str, history: list[dict[str, Any]]) -> None:
        # EN: Redis path also maintains a SET of conversation ids for `/conversations`.
        # PT: No Redis também mantém um SET de ids para listar conversas.
        if self._fallback or self._redis is None:
            self._memory[conv_id] = history
            if conv_id not in self._memory_index:
                self._memory_index.append(conv_id)
            return
        await self._redis.set(
            _KEY_PREFIX + conv_id,
            json.dumps(history, ensure_ascii=False),
            ex=settings.session_ttl_seconds,
        )
        await self._redis.sadd(_INDEX_KEY, conv_id)

    async def list_ids(self) -> list[str]:
        if self._fallback or self._redis is None:
            return list(self._memory_index)
        members = await self._redis.smembers(_INDEX_KEY)
        return sorted(members)

    async def delete(self, conv_id: str) -> None:
        if self._fallback or self._redis is None:
            self._memory.pop(conv_id, None)
            if conv_id in self._memory_index:
                self._memory_index.remove(conv_id)
            return
        await self._redis.delete(_KEY_PREFIX + conv_id)
        await self._redis.srem(_INDEX_KEY, conv_id)


session_store = SessionStore()
