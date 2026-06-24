"""Stripe component — payment processing with checkout sessions and webhooks."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def register(app, settings):
    """Register Stripe routes and tasks with the FastAPI application."""
    from app.components.stripe.api import router

    app.include_router(router, prefix="")

    from app.components.stripe import tasks  # noqa: F401 — registers tasks

    logger.info("stripe_component_activated")
