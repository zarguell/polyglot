"""WebSockets component — room-based real-time connections."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def register(app, settings):
    """Register WebSocket routes. ``app`` is None in the worker process."""
    if app is not None:
        from app.components.websockets.api import router

        app.include_router(router, prefix="")

    logger.info("websockets_component_activated")
