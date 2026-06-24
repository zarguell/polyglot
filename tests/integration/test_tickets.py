"""Integration tests for the support ticket system.

Covers the full ticket API surface: public creation, authenticated
list/detail/update, comments, agent queue, search, admin reports, and
the complete status lifecycle including reopening.
"""

from __future__ import annotations

import base64
import json

import pytest
from httpx import AsyncClient
from itsdangerous import TimestampSigner
from sqlalchemy import select

from app.core.config import settings
from app.main import SESSION_COOKIE_NAME
from app.models.ticket_event import TicketEvent

# ── Helpers ────────────────────────────────────────────────────────────────────


def _ticket_payload(**overrides: str) -> dict[str, str]:
    """Build a valid ticket-creation payload with optional overrides."""
    payload: dict[str, str] = {
        "customer_email": "customer@example.com",
        "customer_name": "Jane Customer",
        "subject": "Cannot log in to my account",
        "description": "I keep getting an error when I try to log in.",
        "priority": "medium",
    }
    payload.update(overrides)
    return payload


async def _create_ticket(client: AsyncClient, **overrides: str) -> dict:
    """POST a ticket via the API and return the parsed response JSON."""
    resp = await client.post("/api/tickets", json=_ticket_payload(**overrides))
    assert resp.status_code == 201, f"Ticket creation failed: {resp.text}"
    return resp.json()


def _enable_csrf(client: AsyncClient) -> AsyncClient:
    """Add a CSRF-enabled session cookie without authentication.

    The CSRF middleware requires a session containing ``csrf_token`` plus a
    matching ``X-CSRFToken`` header.  This seeds both so that public POST
    endpoints (which need CSRF but not auth) work in tests.
    """
    session_data = {"csrf_token": "public-csrf-token"}
    data = base64.b64encode(json.dumps(session_data).encode("utf-8"))
    signer = TimestampSigner(settings.secret_key.get_secret_value())
    signed = signer.sign(data).decode("utf-8")
    client.cookies.set(SESSION_COOKIE_NAME, signed)
    client.headers["X-CSRFToken"] = "public-csrf-token"
    return client


async def _transition(auth_client: AsyncClient, ticket_id: str, status: str) -> dict:
    """PATCH a ticket to ``status`` and return the parsed response JSON."""
    resp = await auth_client.patch(f"/api/tickets/{ticket_id}", json={"status": status})
    assert resp.status_code == 200, f"Transition to '{status}' failed: {resp.text}"
    return resp.json()


# ── Public: create ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_ticket_public(client: AsyncClient):
    """POST /api/tickets without auth returns 201 with correct fields."""
    csrf_client = _enable_csrf(client)
    resp = await csrf_client.post("/api/tickets", json=_ticket_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "open"
    assert data["priority"] == "medium"
    assert data["customer_email"] == "customer@example.com"
    assert data["customer_name"] == "Jane Customer"
    assert data["subject"] == "Cannot log in to my account"
    assert data["description"] == "I keep getting an error when I try to log in."
    assert data["id"]
    assert data["assigned_agent_id"] is None
    assert data["resolved_at"] is None
    assert data["closed_at"] is None


@pytest.mark.asyncio
async def test_create_ticket_invalid_priority(client: AsyncClient):
    """POST with an invalid priority returns 422."""
    csrf_client = _enable_csrf(client)
    resp = await csrf_client.post("/api/tickets", json=_ticket_payload(priority="super-urgent"))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_ticket_missing_fields(client: AsyncClient):
    """POST with missing required fields returns 422."""
    csrf_client = _enable_csrf(client)
    resp = await csrf_client.post("/api/tickets", json={})
    assert resp.status_code == 422


# ── Authenticated: list ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_tickets_requires_auth(client: AsyncClient):
    """GET /api/tickets without auth returns 401."""
    resp = await client.get("/api/tickets")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_tickets_authenticated(auth_client: AsyncClient):
    """Authenticated admin sees all tickets in the list."""
    await _create_ticket(auth_client, subject="First ticket")
    await _create_ticket(auth_client, subject="Second ticket")

    resp = await auth_client.get("/api/tickets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    subjects = {t["subject"] for t in data["tickets"]}
    assert subjects == {"First ticket", "Second ticket"}


# ── Authenticated: detail ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_ticket_detail(auth_client: AsyncClient):
    """GET /api/tickets/{id} returns ticket with creation event and no comments."""
    ticket = await _create_ticket(auth_client)

    resp = await auth_client.get(f"/api/tickets/{ticket['id']}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["ticket"]["id"] == ticket["id"]
    assert data["ticket"]["status"] == "open"

    # Creation event is present
    assert len(data["events"]) >= 1
    creation_event = data["events"][0]
    assert creation_event["to_status"] == "open"
    assert creation_event["notes"] == "Ticket created"

    # No comments yet
    assert data["comments"] == []


# ── Authenticated: update ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_ticket_status(auth_client: AsyncClient):
    """PATCH a ticket from open to assigned succeeds."""
    ticket = await _create_ticket(auth_client)

    resp = await auth_client.patch(f"/api/tickets/{ticket['id']}", json={"status": "assigned"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "assigned"


@pytest.mark.asyncio
async def test_invalid_status_transition(auth_client: AsyncClient):
    """PATCH open -> resolved is not a valid transition; returns 422."""
    ticket = await _create_ticket(auth_client)

    resp = await auth_client.patch(f"/api/tickets/{ticket['id']}", json={"status": "resolved"})
    assert resp.status_code == 422


# ── Authenticated: comments ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_comment(auth_client: AsyncClient):
    """POST a public comment and verify it appears in the ticket detail."""
    ticket = await _create_ticket(auth_client)

    resp = await auth_client.post(
        f"/api/tickets/{ticket['id']}/comments",
        json={"body": "Looking into this issue."},
    )
    assert resp.status_code == 201
    comment = resp.json()
    assert comment["body"] == "Looking into this issue."
    assert comment["is_internal"] is False
    assert comment["ticket_id"] == ticket["id"]

    # Comment appears in the detail response
    detail = await auth_client.get(f"/api/tickets/{ticket['id']}")
    assert detail.status_code == 200
    comments = detail.json()["comments"]
    assert len(comments) == 1
    assert comments[0]["body"] == "Looking into this issue."


@pytest.mark.asyncio
async def test_add_internal_comment(auth_client: AsyncClient):
    """POST a comment with is_internal=true and verify the flag is set."""
    ticket = await _create_ticket(auth_client)

    resp = await auth_client.post(
        f"/api/tickets/{ticket['id']}/comments",
        json={"body": "Internal note: escalate to DB team.", "is_internal": True},
    )
    assert resp.status_code == 201
    assert resp.json()["is_internal"] is True


# ── Authenticated: queue ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_queue(auth_client: AsyncClient):
    """GET /api/queue returns unassigned active tickets."""
    await _create_ticket(auth_client, subject="Queue item", priority="high")

    resp = await auth_client.get("/api/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert any(t["subject"] == "Queue item" for t in data["tickets"])


# ── Authenticated: search ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_tickets(auth_client: AsyncClient):
    """GET /api/tickets/search?q= matches subject and description."""
    await _create_ticket(
        auth_client,
        subject="Urgent server down",
        description="Production server is offline.",
    )

    resp = await auth_client.get("/api/tickets/search?q=server")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert any("server" in t["subject"].lower() for t in data["tickets"])


# ── Admin: reports ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_reports(auth_client: AsyncClient):
    """GET /api/admin/reports returns aggregated counts by status and priority."""
    await _create_ticket(auth_client, subject="A", priority="high")
    ticket_closed = await _create_ticket(auth_client, subject="B", priority="low")
    await _create_ticket(auth_client, subject="C", priority="medium")

    # Transition one ticket to closed (open -> closed is valid)
    await _transition(auth_client, ticket_closed["id"], "closed")

    resp = await auth_client.get("/api/admin/reports")
    assert resp.status_code == 200
    data = resp.json()

    assert data["by_status"]["open"] == 2
    assert data["by_status"]["closed"] == 1

    assert data["by_priority"]["high"] == 1
    assert data["by_priority"]["low"] == 1
    assert data["by_priority"]["medium"] == 1

    # No agents assigned — all tickets are "unassigned"
    assert data["by_agent"]["unassigned"] == 3


# ── Lifecycle ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_ticket_lifecycle(auth_client: AsyncClient, db_session):
    """Transition a ticket through open -> assigned -> in_progress -> resolved -> closed."""
    ticket = await _create_ticket(auth_client)
    ticket_id = ticket["id"]

    # open -> assigned
    assert (await _transition(auth_client, ticket_id, "assigned"))["status"] == "assigned"

    # assigned -> in_progress
    assert (await _transition(auth_client, ticket_id, "in_progress"))["status"] == "in_progress"

    # in_progress -> resolved
    resolved = await _transition(auth_client, ticket_id, "resolved")
    assert resolved["status"] == "resolved"
    assert resolved["resolved_at"] is not None

    # resolved -> closed
    closed = await _transition(auth_client, ticket_id, "closed")
    assert closed["status"] == "closed"
    assert closed["closed_at"] is not None

    # Verify TicketEvent records via DB
    result = await db_session.execute(
        select(TicketEvent)
        .where(TicketEvent.ticket_id == ticket["id"])
        .order_by(TicketEvent.created_at.asc())
    )
    events = list(result.scalars().all())
    # 1 creation event + 4 transition events
    assert len(events) == 5

    # Verify the transition sequence
    transitions = [(e.from_status, e.to_status) for e in events]
    assert transitions == [
        (None, "open"),
        ("open", "assigned"),
        ("assigned", "in_progress"),
        ("in_progress", "resolved"),
        ("resolved", "closed"),
    ]


@pytest.mark.asyncio
async def test_reopen_closed_ticket(auth_client: AsyncClient):
    """A closed ticket can be reopened (closed -> open)."""
    ticket = await _create_ticket(auth_client)
    ticket_id = ticket["id"]

    # Drive through the full lifecycle to closed
    for status in ("assigned", "in_progress", "resolved", "closed"):
        await _transition(auth_client, ticket_id, status)

    # Reopen
    reopened = await _transition(auth_client, ticket_id, "open")
    assert reopened["status"] == "open"
    assert reopened["closed_at"] is None
    assert reopened["resolved_at"] is None
