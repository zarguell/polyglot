"""WebSocket message schema."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class WSMessage(BaseModel):
    """Structured WebSocket message."""

    type: str = "message"
    payload: str
    sender: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
