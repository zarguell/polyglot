"""Redis cache background tasks using Procrastinate."""

from __future__ import annotations

import structlog

from app.core.tasks import task_app

logger = structlog.get_logger()


@task_app.task(name="cache.clear_cache")
def clear_cache() -> None:
    """Clear the Redis cache. Can be scheduled periodically."""
    import asyncio

    from app.components.redis_cache.service import CacheService
    from app.core.config import settings

    async def _clear():
        redis_url = settings.redis_url
        cache = CacheService(redis_url=redis_url)
        ok = await cache.clear()
        logger.info("cache_cleared", success=ok)

    asyncio.run(_clear())


@task_app.periodic(cron="0 4 * * *")
def periodic_clear_cache() -> None:
    """Daily cache flush at 4 AM."""
    clear_cache.defer()
