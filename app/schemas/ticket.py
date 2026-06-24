"""Pydantic v2 schemas for the support ticket system."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserBrief(BaseModel):
    """Minimal user representation for nested serialization (e.g. assigned agent)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str


# ── Ticket ─────────────────────────────────────────────────────────────────────


class TicketCreate(BaseModel):
    customer_email: str = Field(min_length=3, max_length=320)
    customer_name: str = Field(min_length=1, max_length=255)
    subject: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1)
    priority: str = Field(default="medium")


class TicketUpdate(BaseModel):
    priority: str | None = Field(default=None)
    status: str | None = Field(default=None)
    assigned_agent_id: uuid.UUID | None = Field(default=None)


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_email: str
    customer_name: str
    subject: str
    description: str
    status: str
    priority: str
    assigned_agent_id: uuid.UUID | None = None
    assigned_agent: UserBrief | None = None
    attachment_paths: list[str] | None = None
    sla_deadline_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]
    count: int


# ── Ticket comment ─────────────────────────────────────────────────────────────


class TicketCommentCreate(BaseModel):
    body: str = Field(min_length=1)
    is_internal: bool = False
    attachment_paths: list[str] | None = None


class TicketCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    is_internal: bool
    attachment_paths: list[str] | None = None
    created_at: datetime


# ── Ticket event ───────────────────────────────────────────────────────────────


class TicketEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ticket_id: uuid.UUID
    actor_id: uuid.UUID | None = None
    from_status: str | None = None
    to_status: str
    notes: str | None = None
    created_at: datetime


# ── Ticket detail (aggregate) ──────────────────────────────────────────────────


class TicketDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket: TicketResponse
    comments: list[TicketCommentResponse] = Field(default_factory=list)
    events: list[TicketEventResponse] = Field(default_factory=list)


# ── SLA policy ─────────────────────────────────────────────────────────────────


class SLAPolicyCreate(BaseModel):
    priority: str = Field(min_length=1, max_length=16)
    response_time_hours: int = Field(gt=0)
    resolution_time_hours: int = Field(gt=0)


class SLAPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    priority: str
    response_time_hours: int
    resolution_time_hours: int
    created_at: datetime
    updated_at: datetime


# ── Admin reports ──────────────────────────────────────────────────────────────


class AdminReportResponse(BaseModel):
    """Aggregated ticket counts for the admin dashboard."""

    by_status: dict[str, int]
    by_priority: dict[str, int]
    by_agent: dict[str, int]
