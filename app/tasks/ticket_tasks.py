"""Procrastinate tasks for the ticket system — periodic SLA maintenance.

These tasks are auto-discovered from ``app/tasks/`` by ``task_app``.  They use
the Procrastinate 2.6+ wrapper pattern: a registered task is wrapped by
``task_app.periodic(...)`` rather than decorating a plain function.
"""

from __future__ import annotations

import structlog

from app.core.tasks import task_app

logger = structlog.get_logger()


@task_app.task(name="tickets.escalate_overdue")
def escalate_overdue() -> None:
    """Escalate tickets past their SLA deadline. Runs every 15 minutes."""
    import asyncio

    from app.core.db import async_session_factory
    from app.services.ticket_service import escalate_overdue_tickets

    async def _run() -> None:
        async with async_session_factory() as db:
            escalated = await escalate_overdue_tickets(db)
            await db.commit()
            logger.info(
                "tickets_escalated", count=len(escalated) if escalated else 0
            )

    asyncio.run(_run())


@task_app.task(name="tickets.close_stale_resolved")
def close_stale_resolved() -> None:
    """Auto-close resolved tickets older than the stale window. Runs daily."""
    import asyncio

    from app.core.db import async_session_factory
    from app.services.ticket_service import close_stale_resolved_tickets

    async def _run() -> None:
        async with async_session_factory() as db:
            closed = await close_stale_resolved_tickets(db)
            await db.commit()
            logger.info("tickets_auto_closed", count=len(closed) if closed else 0)

    asyncio.run(_run())


# ── Periodic triggers (Procrastinate 2.6+ wrapper pattern) ─────────────────────
# The task function must be registered via @task_app.task(...) *before* being
# passed to task_app.periodic(...).  Do NOT decorate a plain function.

periodic_escalate = task_app.periodic(
    cron="*/15 * * * *",
    task_name="tickets.escalate_overdue",
)(escalate_overdue)

periodic_close_stale = task_app.periodic(
    cron="0 3 * * *",
    task_name="tickets.close_stale_resolved",
)(close_stale_resolved)
