"""CacheService — async Redis cache wrapper with hit/miss tracking."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()


class CacheService:
    """Async Redis-backed cache.

    Falls back gracefully when Redis is not available: methods set/get/delete
    return sensible defaults without raising.
    """

    def __init__(self, redis_url: str = "redis://redis:6379/0") -> None:
        self._redis_url = redis_url
        self._client: Any = None
        self._hits = 0
        self._misses = 0

    @property
    def _redis(self):
        if self._client is None:
            import redis.asyncio as aioredis

            self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._client

    async def ping(self) -> bool:
        """Check if Redis is reachable."""
        try:
            return await self._redis.ping()
        except Exception:
            return False

    async def get(self, key: str) -> Any | None:
        """Retrieve a cached value. Tracks hits and misses."""
        try:
            value = await self._redis.get(key)
            if value is None:
                self._misses += 1
                return None
            self._hits += 1
            return value
        except Exception:
            self._misses += 1
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set a cached value with optional TTL (seconds)."""
        try:
            if ttl:
                await self._redis.setex(key, ttl, str(value))
            else:
                await self._redis.set(key, str(value))
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete a cached key."""
        try:
            await self._redis.delete(key)
            return True
        except Exception:
            return False

    async def clear(self) -> bool:
        """Flush all keys from the cache."""
        try:
            await self._redis.flushdb()
            return True
        except Exception:
            return False

    def get_stats(self) -> dict[str, int]:
        """Return current hit/miss counts."""
        return {"hits": self._hits, "misses": self._misses}
