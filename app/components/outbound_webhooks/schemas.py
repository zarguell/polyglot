"""Outbound Webhooks schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SubscriptionCreate(BaseModel):
    """Request to create a new webhook subscription."""

    name: str
    url: str
    secret: str | None = None
    events: list[str] = []


class SubscriptionRead(BaseModel):
    """Response representing a webhook subscription."""

    id: UUID
    name: str
    url: str
    events: list[str]
    is_active: bool
    last_sent_at: datetime | None = None
    failure_count: int = 0
