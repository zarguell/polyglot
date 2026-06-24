"""Stripe schemas."""

from __future__ import annotations

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    """Request to create a Stripe Checkout session."""

    price_id: str | None = None
    success_url: str | None = None
    cancel_url: str | None = None


class CheckoutResponse(BaseModel):
    """Response from a checkout session creation."""

    status: str
    url: str | None = None
    detail: str | None = None
