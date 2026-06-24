"""Unit tests for Redis Cache component."""

from __future__ import annotations

import asyncio
import importlib


def test_import_redis_cache_component():
    """Smoke test: the component module imports cleanly."""
    mod = importlib.import_module("app.components.redis_cache")
    assert hasattr(mod, "register"), "Redis cache component must expose register()"


def test_cache_service_instantiation():
    """CacheService can be created with a Redis URL."""
    from app.components.redis_cache.service import CacheService

    cache = CacheService(redis_url="redis://localhost:6379/0")
    assert cache is not None
    assert cache._redis_url == "redis://localhost:6379/0"


def test_cache_service_stats_initial():
    """Stats start at zero."""
    from app.components.redis_cache.service import CacheService

    cache = CacheService()
    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0


def test_cache_service_ping_unavailable():
    """Ping returns False when Redis is not running."""
    from app.components.redis_cache.service import CacheService

    cache = CacheService(redis_url="redis://nonexistent-host:6379/0")

    async def _run():
        result = await cache.ping()
        assert result is False

    asyncio.run(_run())


def test_cache_service_get_and_set_unavailable():
    """Get and set return sensible defaults when Redis is not available."""
    from app.components.redis_cache.service import CacheService

    cache = CacheService(redis_url="redis://nonexistent-host:6379/0")

    async def _run():
        result = await cache.get("key1")
        assert result is None
        ok = await cache.set("key1", "value1")
        assert ok is False

    asyncio.run(_run())


def test_register_is_callable():
    """register() is a callable function."""
    from app.components.redis_cache import register

    assert callable(register)
    assert register.__name__ == "register"
