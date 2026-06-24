"""SMTP component — email sending with template rendering and retry tasks."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def register(app, settings):
    """Register SMTP routes and tasks. ``app`` is None in the worker process."""
    if app is not None:
        from app.components.smtp.api import router

        app.include_router(router, prefix="")

    from app.components.smtp import tasks  # noqa: F401 — registers tasks

    logger.info("smtp_component_activated")
