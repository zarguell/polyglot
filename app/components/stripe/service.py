"""StripeService — wraps the Stripe Python SDK with sensible defaults."""

from __future__ import annotations

from typing import Any

import structlog

logger = structlog.get_logger()


class StripeService:
    """Stripe API wrapper.

    Gracefully degrades when STRIPE_SECRET_KEY is not configured; all public
    methods return ``{"status": "not_configured"}`` or None.
    """

    def __init__(
        self,
        secret_key: str = "",
        webhook_secret: str = "",
        price_id: str = "",
    ) -> None:
        self._secret_key = secret_key
        self._webhook_secret = webhook_secret
        self._default_price_id = price_id

    def is_configured(self) -> bool:
        return bool(self._secret_key)

    @property
    def _stripe(self):
        import stripe

        stripe.api_key = self._secret_key
        return stripe

    async def create_checkout_session(
        self,
        customer_email: str,
        success_url: str,
        cancel_url: str,
        price_id: str | None = None,
    ) -> str:
        """Create a Stripe Checkout session. Returns the session URL."""
        if not self.is_configured():
            raise ValueError("STRIPE_SECRET_KEY not configured")

        sid = price_id or self._default_price_id
        if not sid:
            raise ValueError("No STRIPE_PRICE_ID configured")

        session = self._stripe.checkout.Session.create(
            customer_email=customer_email,
            line_items=[{"price": sid, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url

    def verify_webhook(self, payload: bytes, signature: str) -> dict[str, Any] | None:
        """Verify and parse a Stripe webhook event. Returns None on failure."""
        if not self.is_configured():
            return None

        try:
            event = self._stripe.Webhook.construct_event(
                payload,
                signature,
                self._webhook_secret,
            )
            return event
        except Exception:
            logger.exception("stripe_webhook_verification_failed")
            return None
