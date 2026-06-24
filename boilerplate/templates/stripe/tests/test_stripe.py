"""Unit tests for Stripe component."""

from __future__ import annotations

import importlib


def test_import_stripe_component():
    """Smoke test: the component module imports cleanly."""
    mod = importlib.import_module("app.components.stripe")
    assert hasattr(mod, "register"), "Stripe component must expose register()"


def test_stripe_service_not_configured():
    """StripeService reports not_configured when secret key is empty."""
    from app.components.stripe.service import StripeService

    service = StripeService(secret_key="")
    assert service.is_configured() is False


def test_stripe_service_configured():
    """StripeService reports configured when secret key is set."""
    from app.components.stripe.service import StripeService

    service = StripeService(secret_key="sk_test_fake")
    assert service.is_configured() is True


def test_webhook_verification_not_configured():
    """verify_webhook returns None when not configured."""
    from app.components.stripe.service import StripeService

    service = StripeService(secret_key="")
    result = service.verify_webhook(b"{}", "sig_fake")
    assert result is None


def test_checkout_request_schema():
    """CheckoutRequest accepts optional fields."""
    from app.components.stripe.schemas import CheckoutRequest

    req = CheckoutRequest(price_id="price_123", success_url="https://example.com/success")
    assert req.price_id == "price_123"
    assert req.success_url == "https://example.com/success"
    assert req.cancel_url is None


def test_checkout_response_schema():
    """CheckoutResponse carries status and optional URL."""
    from app.components.stripe.schemas import CheckoutResponse

    resp = CheckoutResponse(status="ok", url="https://checkout.stripe.com/...")
    assert resp.status == "ok"
    assert resp.url is not None


def test_stripe_models_module_imports():
    """Stripe models module exposes StripeCustomer, StripeSubscription, StripeEvent."""
    mod = importlib.import_module("app.components.stripe.models")
    assert hasattr(mod, "StripeCustomer"), "models must expose StripeCustomer"
    assert hasattr(mod, "StripeSubscription"), "models must expose StripeSubscription"
    assert hasattr(mod, "StripeEvent"), "models must expose StripeEvent"


def test_register_is_callable():
    """register() is a callable function."""
    from app.components.stripe import register

    assert callable(register)
    assert register.__name__ == "register"
