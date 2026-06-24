"""Procrastinate task_app and periodic task definitions.

Usage:
    @task_app.task(name="domain.action")
    def my_task(...):
        ...

    # Periodic triggers must wrap an already-registered task (Procrastinate 2.6+ API).
    periodic_my_task = task_app.periodic(
        cron="0 * * * *",
        task_name="domain.action",
    )(my_task)
"""

from __future__ import annotations

from datetime import UTC

import structlog
from procrastinate import App
from procrastinate.contrib.aiopg import AiopgConnector

from app.core.config import settings

logger = structlog.get_logger()

# Build async connection string without +asyncpg suffix for Procrastinate
dsn = str(settings.database_url).replace("+asyncpg", "")

task_app = App(connector=AiopgConnector(dsn=dsn))


@task_app.task(name="example.hello_world")
def hello_world(name: str = "World") -> None:
    """Example task that logs and returns."""
    logger.info("task_executed", task_name="hello_world", name=name)


@task_app.task(name="maintenance.audit_log_retention")
def audit_log_retention(retention_days: int = 90) -> None:
    """Periodic task: prune old audit logs. Runs daily."""
    import asyncio
    from datetime import datetime, timedelta

    from app.core.db import async_session_factory
    from app.models.audit_log import AuditLog

    async def _prune():
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        async with async_session_factory() as db:
            from sqlalchemy import delete

            await db.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff),
            )
            await db.commit()
            logger.info("audit_log_pruned", cutoff=cutoff.isoformat())

    asyncio.run(_prune())


# Procrastinate 2.6+: periodic() wraps an already-registered task (has .name attr).
# The old pattern of decorating a plain wrapper function no longer works.
periodic_audit_log_retention = task_app.periodic(
    cron="0 3 * * *",
    task_name="maintenance.audit_log_retention",
)(audit_log_retention)
