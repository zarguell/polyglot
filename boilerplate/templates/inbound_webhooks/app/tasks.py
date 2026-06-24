"""Inbound Webhooks background tasks using Procrastinate."""

from __future__ import annotations

import asyncio
import uuid

import structlog

from app.components.inbound_webhooks.service import WebhookRegistry
from app.core.db import async_session_factory
from app.core.tasks import task_app

logger = structlog.get_logger()


@task_app.task(name="inbound_webhooks.process_webhook_event")
def process_webhook_event(event_id: str) -> None:
    """Process a received webhook event asynchronously.

    Looks up the event, dispatches to the registered handler, and marks
    the event as processed.
    """

    async def _run():
        from sqlalchemy import select

        from app.components.inbound_webhooks.models import WebhookEvent

        async with async_session_factory() as db:
            result = await db.execute(
                select(WebhookEvent).where(WebhookEvent.id == uuid.UUID(event_id))
            )
            event = result.scalar_one_or_none()

            if not event:
                logger.error("webhook_event_not_found", event_id=event_id)
                return

            if event.processed:
                logger.info("webhook_event_already_processed", event_id=event_id)
                return

            # Dispatch to registered handler if one exists
            registry = _get_registry_sync()
            handler = registry.get_handler(event.provider)

            if handler and event.payload:
                try:
                    handler(event.event_type, event.payload)
                    logger.info(
                        "webhook_handler_called",
                        provider=event.provider,
                        event_id=event_id,
                    )
                except Exception:
                    logger.exception(
                        "webhook_handler_failed",
                        provider=event.provider,
                        event_id=event_id,
                    )

            event.processed = True
            await db.commit()

            logger.info("webhook_event_processed", event_id=event_id)

    asyncio.run(_run())


def _get_registry_sync() -> WebhookRegistry:
    import os

    return WebhookRegistry(default_secret=os.getenv("WEBHOOK_SECRET_DEFAULT", ""))
