"""LDAP/AD background tasks using Procrastinate."""

from __future__ import annotations

import asyncio

import structlog

from app.components.ldap_ad.service import LDAPService
from app.core.db import async_session_factory
from app.core.tasks import task_app

logger = structlog.get_logger()


@task_app.task(name="ldap_ad.sync_ldap_users")
def sync_ldap_users() -> None:
    """Periodic task to synchronize LDAP users into the local User table.

    This task should be scheduled recurringly (e.g., via Procrastinate's
    periodic task system or an external cron trigger).
    """

    async def _sync():
        service = LDAPService()
        if not service.is_configured():
            logger.warning("ldap_sync_not_configured")
            return

        async with async_session_factory() as db:
            result = await service.sync_users(db)
            logger.info(
                "ldap_sync_finished",
                created=result["created"],
                updated=result["updated"],
                skipped=result["skipped"],
            )

    asyncio.run(_sync())
