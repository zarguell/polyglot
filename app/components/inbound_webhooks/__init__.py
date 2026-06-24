"""Inbound Webhooks component — receive and verify webhooks from external providers."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def register(app, settings):
    """Register inbound webhook routes and tasks. ``app`` is None in the worker process."""
    if app is not None:
        from app.components.inbound_webhooks.api import router

        app.include_router(router, prefix="")

    from app.components.inbound_webhooks import tasks  # noqa: F401 — registers tasks
    from app.components.inbound_webhooks.service import get_webhook_registry

    get_webhook_registry().register("email", handle_email_webhook)

    logger.info("inbound_webhooks_component_activated")


def handle_email_webhook(event_type: str, payload: dict) -> None:
    """Create a support ticket from an inbound email webhook payload."""
    import asyncio

    from app.core.db import async_session_factory
    from app.services.ticket_service import create_ticket

    async def _handle() -> None:
        async with async_session_factory() as db:
            await create_ticket(
                db,
                customer_email=payload.get("from", ""),
                customer_name=payload.get("from_name", ""),
                subject=payload.get("subject", ""),
                description=payload.get("body_text", payload.get("body", "")),
                priority=payload.get("priority", "medium"),
            )
            await db.commit()

    asyncio.run(_handle())
