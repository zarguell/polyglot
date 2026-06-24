"""Stripe API routes — checkout sessions and webhooks."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.deps import CurrentUser
from app.components.stripe.schemas import CheckoutRequest
from app.components.stripe.service import StripeService

logger = structlog.get_logger()

router = APIRouter(prefix="/api/stripe", tags=["stripe"])


def _get_stripe_service() -> StripeService:
    import os

    return StripeService(
        secret_key=os.getenv("STRIPE_SECRET_KEY", ""),
        webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
        price_id=os.getenv("STRIPE_PRICE_ID", ""),
    )


@router.post("/checkout")
async def create_checkout(
    payload: CheckoutRequest,
    current_user: CurrentUser,
    service: StripeService = Depends(_get_stripe_service),
) -> dict:
    """Create a Stripe Checkout session. Returns the session URL."""
    if not service.is_configured():
        return {"status": "not_configured", "detail": "STRIPE_SECRET_KEY not set"}

    success_url = payload.success_url or "http://localhost:8000/dashboard"
    cancel_url = payload.cancel_url or "http://localhost:8000/dashboard"

    try:
        session_url = await service.create_checkout_session(
            customer_email=current_user.email,
            success_url=success_url,
            cancel_url=cancel_url,
            price_id=payload.price_id,
        )
        logger.info("stripe_checkout_created", user_id=str(current_user.id))
        return {"status": "ok", "url": session_url}
    except Exception:
        logger.exception("stripe_checkout_failed")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")  # noqa: B904


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    service: StripeService = Depends(_get_stripe_service),
) -> dict:
    """Receive and verify Stripe webhook events."""
    if not service.is_configured():
        return {"status": "not_configured", "detail": "STRIPE_SECRET_KEY not set"}

    payload = await request.body()
    event = service.verify_webhook(payload, stripe_signature or "")
    if event is None:
        logger.warning("stripe_invalid_signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    from app.components.stripe.tasks import handle_stripe_event

    handle_stripe_event.defer(event_type=event["type"], event_data=event)

    logger.info("stripe_webhook_received", event_type=event["type"])
    return {"status": "received", "event_type": event["type"]}
