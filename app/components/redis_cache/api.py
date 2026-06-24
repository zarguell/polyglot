"""Cache API routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.components.redis_cache.service import CacheService

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.get("/status")
async def cache_status() -> dict:
    """Return cache backend status and hit/miss statistics."""
    from app.core.config import settings

    redis_url = settings.redis_url
    cache = CacheService(redis_url=redis_url)

    available = await cache.ping()
    stats = cache.get_stats()

    return {
        "available": available,
        "redis_url_configured": bool(redis_url),
        "hits": stats["hits"],
        "misses": stats["misses"],
        "backend": "redis",
    }
