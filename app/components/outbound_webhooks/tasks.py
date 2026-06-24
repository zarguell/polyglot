"""Outbound Webhooks background tasks with exponential backoff using Procrastinate."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import structlog

from app.components.outbound_webhooks.service import DispatcherService
from app.core.db import async_session_factory
from app.core.tasks import task_app

logger = structlog.get_logger()


@task_app.task(name="outbound_webhooks.dispatch_webhook")
def dispatch_webhook(subscription_id: str, event_type: str, payload: dict) -> None:
    """Dispatch a webhook event to a subscriber with retry and backoff.

    Creates a WebhookDelivery record and updates the subscription's
    last_sent_at and failure_count fields.
    """

    async def _run():
        from sqlalchemy import select

        from app.components.outbound_webhooks.models import (
            WebhookDelivery,
            WebhookSubscription,
        )

        async with async_session_factory() as db:
            result = await db.execute(
                select(WebhookSubscription).where(
                    WebhookSubscription.id == uuid.UUID(subscription_id)
                )
            )
            subscription = result.scalar_one_or_none()

            if not subscription:
                logger.error("subscription_not_found", subscription_id=subscription_id)
                return

            if not subscription.is_active:
                logger.info("subscription_inactive", subscription_id=subscription_id)
                return

            service = DispatcherService()
            status, response_code, response_body = await service.dispatch(
                url=subscription.url,
                secret=subscription.secret,
                event_type=event_type,
                payload=payload,
            )

            # Record delivery attempt
            delivery = WebhookDelivery(
                id=uuid.uuid4(),
                subscription_id=subscription.id,
                event_type=event_type,
                payload=payload,
                status=status,
                response_code=response_code,
                response_body=response_body,
                attempted_at=datetime.now(UTC),
            )
            db.add(delivery)

            # Update subscription stats
            subscription.last_sent_at = datetime.now(UTC)
            if status == "delivered":
                subscription.failure_count = 0
            else:
                subscription.failure_count += 1

            await db.commit()

            logger.info(
                "webhook_dispatched",
                subscription_id=subscription_id,
                event_type=event_type,
                status=status,
                response_code=response_code,
            )

    asyncio.run(_run())
