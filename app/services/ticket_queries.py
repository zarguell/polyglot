"""Read-side ticket queries — list, queue, search, and aggregate reports.

These functions are pure reads (no mutations).  They import only ORM models,
keeping them decoupled from the write-side ``ticket_service``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import PRIORITY_WEIGHT, Ticket
from app.models.user import User

# Statuses considered "active" for queue purposes.
_ACTIVE_QUEUE_STATUSES = ("open", "assigned", "in_progress")


async def list_tickets_for_agent(
    db: AsyncSession, agent_id: uuid.UUID
) -> list[Ticket]:
    """Tickets assigned to ``agent_id`` plus all unassigned tickets."""
    result = await db.execute(
        select(Ticket).where(
            or_(
                Ticket.assigned_agent_id == agent_id,
                Ticket.assigned_agent_id.is_(None),
            )
        )
    )
    return list(result.scalars().all())


async def list_tickets_for_admin(db: AsyncSession) -> list[Ticket]:
    """All tickets, newest first."""
    result = await db.execute(
        select(Ticket).order_by(Ticket.created_at.desc())
    )
    return list(result.scalars().all())


async def get_queue(db: AsyncSession) -> list[Ticket]:
    """Unassigned active tickets ordered by priority weight then creation time."""
    result = await db.execute(
        select(Ticket).where(
            Ticket.assigned_agent_id.is_(None),
            Ticket.status.in_(_ACTIVE_QUEUE_STATUSES),
        )
    )
    tickets = list(result.scalars().all())
    tickets.sort(
        key=lambda t: (-PRIORITY_WEIGHT.get(t.priority, 0), t.created_at)
    )
    return tickets


async def search_tickets(db: AsyncSession, query: str) -> list[Ticket]:
    """Case-insensitive search across ticket subject and description."""
    pattern = f"%{query}%"
    result = await db.execute(
        select(Ticket).where(
            or_(
                Ticket.subject.ilike(pattern),
                Ticket.description.ilike(pattern),
            )
        )
    )
    return list(result.scalars().all())


async def get_admin_reports(db: AsyncSession) -> dict[str, dict[str, int]]:
    """Aggregate counts grouped by status, priority, and assigned agent."""
    status_rows = await db.execute(
        select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
    )
    by_status = {row[0]: row[1] for row in status_rows.all()}

    priority_rows = await db.execute(
        select(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority)
    )
    by_priority = {row[0]: row[1] for row in priority_rows.all()}

    agent_rows = await db.execute(
        select(Ticket.assigned_agent_id, func.count(Ticket.id)).group_by(
            Ticket.assigned_agent_id
        )
    )
    by_agent: dict[str, int] = {}
    for agent_id, count in agent_rows.all():
        key = str(agent_id) if agent_id is not None else "unassigned"
        by_agent[key] = count

    return {"by_status": by_status, "by_priority": by_priority, "by_agent": by_agent}


async def get_agent_brief(
    db: AsyncSession, agent_id: uuid.UUID
) -> User | None:
    """Return the User for an agent ID, or ``None``."""
    result = await db.execute(select(User).where(User.id == agent_id))
    return result.scalar_one_or_none()
