"""FSM Workflows component — finite-state machine engine for entity lifecycle management."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def register(app, settings):
    """Register FSM Workflow routes and tasks with the FastAPI application."""
    from app.components.fsm_workflows.api import router

    app.include_router(router, prefix="")

    from app.components.fsm_workflows import tasks  # noqa: F401 — registers tasks

    logger.info("fsm_workflows_component_activated")
