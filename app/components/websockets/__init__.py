"""WebSockets component — room-based real-time connections."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def register(app, settings):
    """Register WebSocket routes with the FastAPI application."""
    from app.components.websockets.api import router

    app.include_router(router, prefix="")

    logger.info("websockets_component_activated")
