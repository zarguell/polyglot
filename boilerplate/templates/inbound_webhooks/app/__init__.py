"""Inbound Webhooks component — receive and verify webhooks from external providers."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def register(app, settings):
    """Register inbound webhook routes and tasks with the FastAPI application."""
    from app.components.inbound_webhooks.api import router

    app.include_router(router, prefix="")

    from app.components.inbound_webhooks import tasks  # noqa: F401 — registers tasks

    logger.info("inbound_webhooks_component_activated")
