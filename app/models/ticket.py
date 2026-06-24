"""Ticket model — the core support ticket entity."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, Base, uuid_pk

# Valid status transitions: each status maps to the set of statuses it may move to.
VALID_TRANSITIONS: dict[str, set[str]] = {
    "open": {"assigned", "closed"},
    "assigned": {"in_progress", "open"},
    "in_progress": {"resolved", "assigned"},
    "resolved": {"closed", "in_progress"},
    "closed": {"open"},
}

VALID_STATUSES = set(VALID_TRANSITIONS)
VALID_PRIORITIES = {"low", "medium", "high", "critical"}

# Priority ordering weight for queue sorting (higher = more urgent).
PRIORITY_WEIGHT: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


class Ticket(AuditMixin, Base):
    """A customer support ticket."""

    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = uuid_pk()
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    attachment_paths: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    sla_deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    assigned_agent = relationship(
        "User",
        lazy="joined",
        foreign_keys=[assigned_agent_id],
    )
    comments = relationship(
        "TicketComment",
        lazy="selectin",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
    events = relationship(
        "TicketEvent",
        lazy="noload",
        back_populates="ticket",
        cascade="all, delete-orphan",
    )
