"""Redis cache component — async caching with statistics."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def register(app, settings):
    """Register cache routes and tasks. ``app`` is None in the worker process."""
    if app is not None:
        from app.components.redis_cache.api import router

        app.include_router(router, prefix="")

    from app.components.redis_cache import tasks  # noqa: F401 — registers tasks

    logger.info("redis_cache_component_activated")
