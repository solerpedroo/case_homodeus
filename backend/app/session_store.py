"""Redis-backed conversation store.

The API stays stateless: every request reads/writes the conversation by id from
Redis. Falls back to an in-memory dict if Redis is unavailable so local dev and
unit tests don't require the dependency to be running.
"""
from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from app.config import settings
from app.logging_config import logger

_KEY_PREFIX = "homodeus:conv:"
_INDEX_KEY = "homodeus:conv:index"


class SessionStore:
    def __init__(self) -> None:
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
