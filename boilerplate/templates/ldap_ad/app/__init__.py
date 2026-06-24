"""LDAP/AD component — synchronize users from an LDAP directory or Active Directory."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def register(app, settings):
    """Register LDAP routes and tasks with the FastAPI application."""
    from app.components.ldap_ad.api import router

    app.include_router(router, prefix="")

    from app.components.ldap_ad import tasks  # noqa: F401 — registers tasks

    logger.info("ldap_ad_component_activated")
