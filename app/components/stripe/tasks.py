"""Stripe background tasks using Procrastinate."""

from __future__ import annotations

import structlog

from app.core.tasks import task_app

logger = structlog.get_logger()


@task_app.task(name="stripe.sync_stripe_customer")
def sync_stripe_customer(user_id: str) -> None:
    """Sync a Polyglot user with their Stripe customer record."""
    import asyncio
    import uuid

    from sqlalchemy import select

    from app.components.stripe.models import StripeCustomer
    from app.core.db import async_session_factory

    async def _sync():
        from app.core.config import settings
        if not settings.stripe_secret_key:
            logger.warning("stripe_task_not_configured")
            return

        async with async_session_factory() as db:
            result = await db.execute(
                select(StripeCustomer).where(StripeCustomer.user_id == uuid.UUID(user_id))
            )
            existing = result.scalar_one_or_none()
            if existing:
                logger.info("stripe_customer_already_synced", user_id=user_id)
                return

        logger.info("stripe_customer_needs_sync", user_id=user_id)

    asyncio.run(_sync())


@task_app.task(name="stripe.handle_stripe_event", retry=3)
def handle_stripe_event(event_type: str, event_data: dict) -> None:
    """Process a Stripe webhook event asynchronously."""
    import asyncio
    import json

    from sqlalchemy import select

    from app.components.stripe.models import StripeEvent
    from app.core.db import async_session_factory

    async def _handle():
        from app.core.config import settings
        if not settings.stripe_secret_key:
            logger.warning("stripe_task_not_configured")
            return

        # Idempotency check — skip duplicate events
        event_id = event_data.get("id", "")
        async with async_session_factory() as db:
            result = await db.execute(select(StripeEvent).where(StripeEvent.event_id == event_id))
            if result.scalar_one_or_none():
                logger.info("stripe_event_already_processed", event_id=event_id)
                return

            record = StripeEvent(
                event_id=event_id,
                event_type=event_type,
                event_data=json.dumps(event_data),
                processed=True,
            )
            db.add(record)
            await db.commit()

        logger.info("stripe_event_processed", event_type=event_type, event_id=event_id)

    asyncio.run(_handle())
