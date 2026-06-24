"""File storage component — upload, download, and manage files."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def register(app, settings):
    """Register file storage routes. ``app`` is None in the worker process."""
    if app is not None:
        from app.components.file_storage.api import router

        app.include_router(router, prefix="")

    logger.info("file_storage_component_activated")
