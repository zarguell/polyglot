from __future__ import annotations

from datetime import UTC

import structlog
from procrastinate import AiopgConnector, App

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


@task_app.periodic(cron="0 3 * * *")
def periodic_audit_log_retention() -> None:
    """Wrapper for the cron-scheduled version."""
    audit_log_retention.defer(retention_days=90)
