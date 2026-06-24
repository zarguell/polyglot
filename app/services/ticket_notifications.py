"""Ticket email notifications — defer to the SMTP Procrastinate task.

These helpers compose the email body and defer delivery to
``app.components.smtp.tasks.send_email`` so sending happens out-of-band with
automatic retry.  No SMTP I/O happens in the request path.
"""

from __future__ import annotations

import structlog

from app.components.smtp.tasks import send_email
from app.models.ticket import Ticket
from app.models.user import User

logger = structlog.get_logger()


def send_ticket_created_notification(ticket: Ticket) -> None:
    """Auto-reply to the customer acknowledging their new ticket."""
    body = (
        f"Hi {ticket.customer_name},\n\n"
        f"We have received your support request (#{ticket.id}).\n\n"
        f"Subject: {ticket.subject}\n"
        f"Priority: {ticket.priority}\n\n"
        "We will get back to you as soon as possible.\n\n"
        "— Support Team"
    )
    try:
        send_email.defer(
            to=ticket.customer_email,
            subject=f"[#{ticket.id}] We received your request: {ticket.subject}",
            body=body,
        )
        logger.info("ticket_created_notification_deferred", ticket_id=str(ticket.id))
    except Exception:
        logger.warning("ticket_created_notification_skip", ticket_id=str(ticket.id))


def send_agent_assigned_notification(ticket: Ticket, agent: User) -> None:
    """Notify an agent that a ticket has been assigned to them."""
    body = (
        f"Hi {agent.display_name},\n\n"
        f"A ticket has been assigned to you (#{ticket.id}).\n\n"
        f"Subject: {ticket.subject}\n"
        f"Priority: {ticket.priority}\n"
        f"Customer: {ticket.customer_name} <{ticket.customer_email}>\n\n"
        f"Description:\n{ticket.description}\n"
    )
    try:
        send_email.defer(
            to=agent.email,
            subject=f"[#{ticket.id}] New ticket assigned: {ticket.subject}",
            body=body,
        )
        logger.info(
            "agent_assigned_notification_deferred",
            ticket_id=str(ticket.id),
            agent_id=str(agent.id),
        )
    except Exception:
        logger.warning("agent_assigned_notification_skip", ticket_id=str(ticket.id))


def send_ticket_resolved_notification(ticket: Ticket) -> None:
    """Notify the customer that their ticket has been resolved."""
    body = (
        f"Hi {ticket.customer_name},\n\n"
        f"Your support request (#{ticket.id}) has been marked as resolved.\n\n"
        f"Subject: {ticket.subject}\n\n"
        "If you are still experiencing issues, simply reply to this email and "
        "the ticket will be reopened.\n\n"
        "— Support Team"
    )
    try:
        send_email.defer(
            to=ticket.customer_email,
            subject=f"[#{ticket.id}] Your request has been resolved: {ticket.subject}",
            body=body,
        )
        logger.info("ticket_resolved_notification_deferred", ticket_id=str(ticket.id))
    except Exception:
        logger.warning("ticket_resolved_notification_skip", ticket_id=str(ticket.id))
