"""Outbound Webhooks API routes — CRUD for subscriptions and test dispatch."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentUser
from app.components.outbound_webhooks.models import WebhookSubscription
from app.components.outbound_webhooks.schemas import SubscriptionCreate, SubscriptionRead
from app.components.outbound_webhooks.tasks import dispatch_webhook
from app.core.db import async_session_factory

logger = structlog.get_logger()

router = APIRouter(prefix="/api/webhook-subscriptions", tags=["outbound-webhooks"])


@router.post("")
async def create_subscription(payload: SubscriptionCreate, current_user: CurrentUser) -> dict:
    """Create a new webhook subscription."""
    async with async_session_factory() as db:
        subscription = WebhookSubscription(
            id=uuid.uuid4(),
            name=payload.name,
            url=payload.url,
            secret=payload.secret,
            events=payload.events,
            is_active=True,
            failure_count=0,
        )
        db.add(subscription)
        await db.commit()

    logger.info("webhook_subscription_created", name=payload.name, id=str(subscription.id))
    return {"status": "ok", "id": str(subscription.id)}


@router.get("")
async def list_subscriptions(current_user: CurrentUser) -> list[SubscriptionRead]:
    """List all webhook subscriptions."""
    async with async_session_factory() as db:
        result = await db.execute(select(WebhookSubscription).order_by(WebhookSubscription.name))
        subscriptions = result.scalars().all()

    return [
        SubscriptionRead(
            id=s.id,
            name=s.name,
            url=s.url,
            events=s.events or [],
            is_active=s.is_active,
            last_sent_at=s.last_sent_at,
            failure_count=s.failure_count,
        )
        for s in subscriptions
    ]


@router.get("/{subscription_id}")
async def get_subscription(subscription_id: str, current_user: CurrentUser) -> SubscriptionRead:
    """Get a single subscription by ID."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(WebhookSubscription).where(WebhookSubscription.id == uuid.UUID(subscription_id))
        )
        s = result.scalar_one_or_none()

    if not s:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return SubscriptionRead(
        id=s.id,
        name=s.name,
        url=s.url,
        events=s.events or [],
        is_active=s.is_active,
        last_sent_at=s.last_sent_at,
        failure_count=s.failure_count,
    )


@router.post("/{subscription_id}/test")
async def test_subscription(subscription_id: str, current_user: CurrentUser) -> dict:
    """Send a test webhook to a subscription."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(WebhookSubscription).where(WebhookSubscription.id == uuid.UUID(subscription_id))
        )
        subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    dispatch_webhook.defer(
        subscription_id=str(subscription.id),
        event_type="test",
        payload={"message": "Test webhook from Polyglot"},
    )

    logger.info("test_webhook_queued", subscription_id=str(subscription.id))
    return {"status": "ok", "message": "Test webhook queued"}
