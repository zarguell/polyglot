"""Inbound Webhooks API routes — generic webhook receiver."""

from __future__ import annotations

import os
import uuid

import structlog
from fastapi import APIRouter, Header, Request

from app.components.inbound_webhooks.models import WebhookEvent
from app.components.inbound_webhooks.schemas import WebhookResponse
from app.components.inbound_webhooks.service import WebhookRegistry
from app.components.inbound_webhooks.tasks import process_webhook_event
from app.core.db import async_session_factory

logger = structlog.get_logger()

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

_registry: WebhookRegistry | None = None


def _get_registry() -> WebhookRegistry:
    global _registry
    if _registry is None:
        _registry = WebhookRegistry(default_secret=os.getenv("WEBHOOK_SECRET_DEFAULT", ""))
    return _registry


@router.post("/{provider}")
async def receive_webhook(
    provider: str,
    request: Request,
    x_signature: str | None = Header(None, alias="x-webhook-signature"),
) -> WebhookResponse:
    """Receive a webhook from an external provider.

    The webhook is stored, verified (if a signature is present), and
    dispatched to the registered handler via a background task.
    """
    registry = _get_registry()
    payload = await request.body()

    # Collect headers for audit
    headers = dict(request.headers)
    signature = x_signature or headers.get("x-webhook-signature", "")

    # Determine event type from headers or payload
    event_type = headers.get("x-webhook-event", provider)

    # Verify signature if present
    verified = False
    if signature:
        verified = registry.verify_signature(payload, signature)

    # Store the event
    import json

    async with async_session_factory() as db:
        event = WebhookEvent(
            id=uuid.uuid4(),
            provider=provider,
            event_type=event_type,
            payload=json.loads(payload) if payload else None,
            headers=dict(headers),
            signature=signature,
            verified=verified,
            processed=False,
        )
        db.add(event)
        await db.commit()

    logger.info(
        "webhook_received",
        provider=provider,
        event_type=event_type,
        event_id=str(event.id),
        verified=verified,
    )

    # Dispatch to background processor
    process_webhook_event.defer(event_id=str(event.id))

    return WebhookResponse(
        status="received",
        event_id=str(event.id),
        provider=provider,
    )
