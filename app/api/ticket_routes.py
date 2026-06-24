"""Support ticket API routes — JSON endpoints for the ticket system.

Public endpoint: ``POST /api/tickets`` (create) requires no auth.  All other
endpoints require authentication; admin-only endpoints use :data:`AdminUser`.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Query

from app.api.deps import AdminUser, CurrentUser, DbDeps
from app.api.sse import broadcast_sse_event
from app.core.errors import ForbiddenError
from app.models.ticket import Ticket
from app.schemas.ticket import (
    AdminReportResponse,
    TicketCommentCreate,
    TicketCommentResponse,
    TicketCreate,
    TicketDetailResponse,
    TicketEventResponse,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)
from app.services import ticket_service
from app.services.ticket_notifications import (
    send_agent_assigned_notification,
    send_ticket_created_notification,
    send_ticket_resolved_notification,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["tickets"])


def _to_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse.model_validate(ticket)


def _assert_can_modify(ticket: Ticket, user) -> None:
    """Only the assigned agent or an admin may modify a ticket."""
    if user.is_admin:
        return
    if ticket.assigned_agent_id is None or ticket.assigned_agent_id != user.id:
        raise ForbiddenError("Only the assigned agent or an admin may modify this ticket")


# ── Public: create ticket ──────────────────────────────────────────────────────


@router.post("/tickets", response_model=TicketResponse, status_code=201)
async def create_ticket(body: TicketCreate, db: DbDeps):
    """Create a new support ticket. Public endpoint — no auth required."""
    ticket = await ticket_service.create_ticket(
        db,
        customer_email=body.customer_email,
        customer_name=body.customer_name,
        subject=body.subject,
        description=body.description,
        priority=body.priority,
    )
    await db.commit()
    await db.refresh(ticket)
    send_ticket_created_notification(ticket)
    broadcast_sse_event(
        {"type": "ticket_created", "ticket_id": str(ticket.id), "priority": ticket.priority}
    )
    return _to_response(ticket)


# ── Authenticated: list / detail / search ──────────────────────────────────────


@router.get("/tickets", response_model=TicketListResponse)
async def list_tickets(user: CurrentUser, db: DbDeps):
    """List tickets visible to the current user.

    Admins see all tickets; agents see their assigned tickets plus the
    unassigned open queue.
    """
    if user.is_admin:
        tickets = await ticket_service.list_tickets_for_admin(db)
    else:
        tickets = await ticket_service.list_tickets_for_agent(db, user.id)
    items = [_to_response(t) for t in tickets]
    return TicketListResponse(tickets=items, count=len(items))


@router.get("/tickets/search", response_model=TicketListResponse)
async def search_tickets(
    user: CurrentUser,  # noqa: ARG001 — auth gate only
    db: DbDeps,
    q: str = Query(min_length=1, description="Search query"),
):
    """Full-text search across ticket subject and description."""
    tickets = await ticket_service.search_tickets(db, q)
    items = [_to_response(t) for t in tickets]
    return TicketListResponse(tickets=items, count=len(items))


@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket_detail(ticket_id: uuid.UUID, user: CurrentUser, db: DbDeps):
    """Fetch a single ticket with its comments and audit events."""
    ticket = await ticket_service.get_ticket(db, ticket_id)
    comments = await ticket_service.list_comments(db, ticket_id)
    events = await ticket_service.list_events(db, ticket_id)
    return TicketDetailResponse(
        ticket=_to_response(ticket),
        comments=[TicketCommentResponse.model_validate(c) for c in comments],
        events=[TicketEventResponse.model_validate(e) for e in events],
    )


# ── Authenticated: update ──────────────────────────────────────────────────────


@router.patch("/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: uuid.UUID,
    body: TicketUpdate,
    user: CurrentUser,
    db: DbDeps,
):
    """Update a ticket's status, priority, and/or assignment.

    Only the assigned agent or an admin may update.  Status transitions are
    validated server-side.  Notifies the customer on resolution and the agent
    on assignment.
    """
    ticket = await ticket_service.get_ticket(db, ticket_id)
    _assert_can_modify(ticket, user)

    previous_status = ticket.status
    was_resolved = previous_status == "resolved"
    had_agent = ticket.assigned_agent_id

    ticket = await ticket_service.update_ticket(
        db,
        ticket_id,
        actor_id=user.id,
        status=body.status,
        priority=body.priority,
        assigned_agent_id=body.assigned_agent_id,
    )
    await db.commit()
    await db.refresh(ticket)

    # Side-effect notifications (deferred via Procrastinate).
    if body.status == "resolved" and not was_resolved:
        send_ticket_resolved_notification(ticket)
    if body.assigned_agent_id is not None and body.assigned_agent_id != had_agent:
        agent = await ticket_service.get_agent_brief(db, body.assigned_agent_id)
        if agent is not None:
            send_agent_assigned_notification(ticket, agent)

    broadcast_sse_event(
        {
            "type": "ticket_updated",
            "ticket_id": str(ticket.id),
            "status": ticket.status,
            "priority": ticket.priority,
        }
    )
    return _to_response(ticket)


# ── Authenticated: comments ────────────────────────────────────────────────────


@router.post(
    "/tickets/{ticket_id}/comments",
    response_model=TicketCommentResponse,
    status_code=201,
)
async def add_comment(
    ticket_id: uuid.UUID,
    body: TicketCommentCreate,
    user: CurrentUser,
    db: DbDeps,
):
    """Add a comment to a ticket."""
    comment = await ticket_service.add_comment(
        db,
        ticket_id,
        author_id=user.id,
        body=body.body,
        is_internal=body.is_internal,
        attachment_paths=body.attachment_paths,
    )
    await db.commit()
    await db.refresh(comment)
    broadcast_sse_event(
        {"type": "comment_added", "ticket_id": str(ticket_id), "comment_id": str(comment.id)}
    )
    return TicketCommentResponse.model_validate(comment)


# ── Authenticated: agent queue ─────────────────────────────────────────────────


@router.get("/queue", response_model=TicketListResponse)
async def get_queue(user: CurrentUser, db: DbDeps):
    """Return the agent work queue.

    Admins see the full unassigned queue.  Agents with assigned tickets see
    their queue; agents without assignments see the unassigned queue.
    """
    queue = await ticket_service.get_queue(db)
    items = [_to_response(t) for t in queue]
    return TicketListResponse(tickets=items, count=len(items))


# ── Admin-only: reports ────────────────────────────────────────────────────────


@router.get("/admin/reports", response_model=AdminReportResponse)
async def admin_reports(_admin: AdminUser, db: DbDeps):
    """Aggregate ticket counts grouped by status, priority, and assigned agent."""
    reports = await ticket_service.get_admin_reports(db)
    return AdminReportResponse(
        by_status=reports["by_status"],
        by_priority=reports["by_priority"],
        by_agent=reports["by_agent"],
    )
