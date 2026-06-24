"""Automated ticket lifecycle — SLA escalation and stale-resolution auto-close.

These functions run from periodic Procrastinate tasks.  They mutate ticket
state and record audit events.  ``_validate_transition`` is imported from the
write-side ``ticket_service`` to avoid duplicating the transition table.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket
from app.models.ticket_event import TicketEvent
from app.services.ticket_service import _validate_transition

logger = structlog.get_logger()

_ESCALATION_ORDER = ("low", "medium", "high", "critical")
_STALE_RESOLVED_DAYS = 7
_ACTIVE_STATUSES = ("open", "assigned", "in_progress")


async def escalate_overdue_tickets(db: AsyncSession) -> list[Ticket]:
    """Bump the priority of active tickets past their SLA deadline.

    ``critical`` tickets cannot be escalated further.  Returns the list of
    tickets that were escalated.
    """
    now = datetime.now(UTC)
    result = await db.execute(
        select(Ticket).where(
            Ticket.sla_deadline_at.is_not(None),
            Ticket.sla_deadline_at < now,
            Ticket.status.in_(_ACTIVE_STATUSES),
        )
    )
    escalated: list[Ticket] = []
    for ticket in result.scalars().all():
        if ticket.priority == "critical":
            continue
        idx = _ESCALATION_ORDER.index(ticket.priority)
        ticket.priority = _ESCALATION_ORDER[min(idx + 1, len(_ESCALATION_ORDER) - 1)]
        escalated.append(ticket)
        logger.info(
            "ticket_escalated",
            ticket_id=str(ticket.id),
            new_priority=ticket.priority,
        )
    await db.flush()
    return escalated


async def close_stale_resolved_tickets(db: AsyncSession) -> list[Ticket]:
    """Auto-close resolved tickets older than the stale window.

    Returns the list of tickets that were closed.
    """
    cutoff = datetime.now(UTC) - timedelta(days=_STALE_RESOLVED_DAYS)
    result = await db.execute(
        select(Ticket).where(
            Ticket.status == "resolved",
            Ticket.resolved_at.is_not(None),
            Ticket.resolved_at < cutoff,
        )
    )
    closed: list[Ticket] = []
    now = datetime.now(UTC)
    for ticket in result.scalars().all():
        _validate_transition(ticket.status, "closed")
        ticket.status = "closed"
        ticket.closed_at = now
        db.add(
            TicketEvent(
                ticket_id=ticket.id,
                actor_id=None,
                from_status="resolved",
                to_status="closed",
                notes="Auto-closed after stale resolution window",
            )
        )
        closed.append(ticket)
        logger.info("ticket_auto_closed", ticket_id=str(ticket.id))
    await db.flush()
    return closed
