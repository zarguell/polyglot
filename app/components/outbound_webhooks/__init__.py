"""Outbound Webhooks component — dispatch webhook events to external subscribers with retry and backoff."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def register(app, settings):
    """Register outbound webhook routes and tasks. ``app`` is None in the worker process."""
    if app is not None:
        from app.components.outbound_webhooks.api import router

        app.include_router(router, prefix="")

    from app.components.outbound_webhooks import tasks  # noqa: F401 — registers tasks

    logger.info("outbound_webhooks_component_activated")
