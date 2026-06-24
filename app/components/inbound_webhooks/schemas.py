"""Inbound Webhooks schemas."""

from __future__ import annotations

from pydantic import BaseModel


class WebhookResponse(BaseModel):
    """Response returned after receiving a webhook."""

    status: str
    event_id: str | None = None
    provider: str | None = None
