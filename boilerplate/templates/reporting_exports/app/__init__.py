"""Reporting & Exports component — generate CSV, XLSX, and PDF reports via background tasks."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def register(app, settings):
    """Register reporting routes and tasks with the FastAPI application."""
    from app.components.reporting_exports.api import router

    app.include_router(router, prefix="")

    from app.components.reporting_exports import tasks  # noqa: F401 — registers tasks

    logger.info("reporting_exports_component_activated")
