"""Ticket service — write-side business logic for the support ticket system.

Core CRUD, status-transition validation, SLA deadline computation, comments,
and events live here.  Read-side queries are in :mod:`ticket_queries` and
automated lifecycle in :mod:`ticket_lifecycle`; both are re-exported below so
``from app.services import ticket_service`` remains the single import surface.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError
from app.models.sla_policy import SLAPolicy
from app.models.ticket import VALID_PRIORITIES, VALID_TRANSITIONS, Ticket
from app.models.ticket_comment import TicketComment
from app.models.ticket_event import TicketEvent

logger = structlog.get_logger()


class InvalidTransitionError(AppError):
    """Raised when a ticket status transition is not permitted."""

    def __init__(self, from_status: str, to_status: str) -> None:
        super().__init__(
            message=f"Cannot transition ticket from '{from_status}' to '{to_status}'",
            status_code=422,
        )


class InvalidPriorityError(AppError):
    """Raised when an unknown priority value is supplied."""

    def __init__(self, priority: str) -> None:
        super().__init__(
            message=f"Invalid priority: {priority}",
            status_code=422,
        )


def _validate_transition(from_status: str, to_status: str) -> None:
    """Raise :class:`InvalidTransitionError` if the move is not permitted."""
    allowed = VALID_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise InvalidTransitionError(from_status, to_status)


async def compute_sla_deadline(
    db: AsyncSession, priority: str
) -> datetime | None:
    """Return the SLA resolution deadline for ``priority``, or ``None``.

    Looks up the matching ``SLAPolicy`` and adds ``resolution_time_hours`` to
    the current UTC time.  When no policy exists, returns ``None``.
    """
    result = await db.execute(
        select(SLAPolicy).where(SLAPolicy.priority == priority)
    )
    policy = result.scalar_one_or_none()
    if policy is None:
        return None
    return datetime.now(UTC) + timedelta(hours=policy.resolution_time_hours)


async def create_ticket(
    db: AsyncSession,
    *,
    customer_email: str,
    customer_name: str,
    subject: str,
    description: str,
    priority: str = "medium",
) -> Ticket:
    """Create a new ticket, computing the SLA deadline from the priority policy."""
    if priority not in VALID_PRIORITIES:
        raise InvalidPriorityError(priority)

    sla_deadline = await compute_sla_deadline(db, priority)
    ticket = Ticket(
        customer_email=customer_email,
        customer_name=customer_name,
        subject=subject,
        description=description,
        status="open",
        priority=priority,
        sla_deadline_at=sla_deadline,
    )
    db.add(ticket)
    await db.flush()

    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            actor_id=None,
            from_status=None,
            to_status="open",
            notes="Ticket created",
        )
    )
    await db.flush()
    logger.info(
        "ticket_created",
        ticket_id=str(ticket.id),
        priority=priority,
        sla_deadline=sla_deadline.isoformat() if sla_deadline else None,
    )
    return ticket


async def get_ticket(db: AsyncSession, ticket_id: uuid.UUID) -> Ticket:
    """Fetch a single ticket by ID. Raises ``NotFoundError`` if absent."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise NotFoundError("Ticket not found")
    return ticket


async def update_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    *,
    actor_id: uuid.UUID,
    status: str | None = None,
    priority: str | None = None,
    assigned_agent_id: uuid.UUID | None = None,
) -> Ticket:
    """Update a ticket's status, priority, and/or assignment.

    Status transitions are validated against :data:`VALID_TRANSITIONS`.
    Transitioning to ``resolved`` stamps ``resolved_at``; ``closed`` stamps
    ``closed_at``; reopening clears terminal timestamps.  Each status change
    is recorded as a :class:`TicketEvent`.
    """
    ticket = await get_ticket(db, ticket_id)

    if status is not None and status != ticket.status:
        _validate_transition(ticket.status, status)
        previous = ticket.status
        ticket.status = status
        now = datetime.now(UTC)
        if status == "resolved":
            ticket.resolved_at = now
        elif status == "closed":
            ticket.closed_at = now
        elif status in {"open", "assigned", "in_progress"}:
            ticket.resolved_at = None
            ticket.closed_at = None
        db.add(
            TicketEvent(
                ticket_id=ticket.id,
                actor_id=actor_id,
                from_status=previous,
                to_status=status,
            )
        )
        logger.info(
            "ticket_status_changed",
            ticket_id=str(ticket.id),
            from_status=previous,
            to_status=status,
        )

    if priority is not None and priority != ticket.priority:
        if priority not in VALID_PRIORITIES:
            raise InvalidPriorityError(priority)
        ticket.priority = priority
        ticket.sla_deadline_at = await compute_sla_deadline(db, priority)
        logger.info(
            "ticket_priority_changed",
            ticket_id=str(ticket.id),
            priority=priority,
        )

    if assigned_agent_id is not None:
        ticket.assigned_agent_id = assigned_agent_id
        logger.info(
            "ticket_assigned",
            ticket_id=str(ticket.id),
            agent_id=str(assigned_agent_id),
        )

    await db.flush()
    return ticket


async def add_comment(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    *,
    author_id: uuid.UUID,
    body: str,
    is_internal: bool = False,
    attachment_paths: list[str] | None = None,
) -> TicketComment:
    """Append a comment to a ticket."""
    await get_ticket(db, ticket_id)

    comment = TicketComment(
        ticket_id=ticket_id,
        author_id=author_id,
        body=body,
        is_internal=is_internal,
        attachment_paths=attachment_paths,
    )
    db.add(comment)
    await db.flush()
    return comment


async def list_comments(
    db: AsyncSession, ticket_id: uuid.UUID
) -> list[TicketComment]:
    """All comments on a ticket, oldest first."""
    result = await db.execute(
        select(TicketComment)
        .where(TicketComment.ticket_id == ticket_id)
        .order_by(TicketComment.created_at.asc())
    )
    return list(result.scalars().all())


async def list_events(
    db: AsyncSession, ticket_id: uuid.UUID
) -> list[TicketEvent]:
    """All audit events for a ticket, oldest first."""
    result = await db.execute(
        select(TicketEvent)
        .where(TicketEvent.ticket_id == ticket_id)
        .order_by(TicketEvent.created_at.asc())
    )
    return list(result.scalars().all())


# ── Re-exports: preserve ``from app.services import ticket_service`` surface ──
from app.services.ticket_lifecycle import (  # noqa: E402, F401
    close_stale_resolved_tickets,
    escalate_overdue_tickets,
)
from app.services.ticket_queries import (  # noqa: E402, F401
    get_admin_reports,
    get_agent_brief,
    get_queue,
    list_tickets_for_admin,
    list_tickets_for_agent,
    search_tickets,
)

__all__ = [
    "InvalidTransitionError",
    "InvalidPriorityError",
    "compute_sla_deadline",
    "create_ticket",
    "get_ticket",
    "update_ticket",
    "add_comment",
    "list_comments",
    "list_events",
    "list_tickets_for_agent",
    "list_tickets_for_admin",
    "get_queue",
    "search_tickets",
    "get_admin_reports",
    "get_agent_brief",
    "escalate_overdue_tickets",
    "close_stale_resolved_tickets",
]
