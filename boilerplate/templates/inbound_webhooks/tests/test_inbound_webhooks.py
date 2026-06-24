"""Unit tests for Inbound Webhooks component."""

from __future__ import annotations

import importlib


def test_import_inbound_webhooks_component():
    """Smoke test: the component module imports cleanly."""
    mod = importlib.import_module("app.components.inbound_webhooks")
    assert hasattr(mod, "register"), "Inbound Webhooks component must expose register()"


def test_register_is_callable():
    """register() is a callable function."""
    from app.components.inbound_webhooks import register

    assert callable(register)
    assert register.__name__ == "register"


def test_webhook_registry_register_handler():
    """WebhookRegistry can register and look up handlers."""
    from app.components.inbound_webhooks.service import WebhookRegistry

    registry = WebhookRegistry()

    def my_handler(event_type: str, payload: dict) -> None:
        pass

    registry.register("stripe", my_handler)

    handler = registry.get_handler("stripe")
    assert handler is not None

    unknown = registry.get_handler("unknown")
    assert unknown is None


def test_webhook_registry_list_providers():
    """WebhookRegistry lists registered provider names."""
    from app.components.inbound_webhooks.service import WebhookRegistry

    registry = WebhookRegistry()

    def handler(event_type: str, payload: dict) -> None:
        pass

    registry.register("github", handler)
    registry.register("slack", handler)

    providers = registry.list_providers()
    assert "github" in providers
    assert "slack" in providers


def test_hmac_verification_success():
    """verify_signature returns True for a valid HMAC-SHA256 signature."""
    import hashlib
    import hmac

    from app.components.inbound_webhooks.service import WebhookRegistry

    secret = "test_secret"
    payload = b'{"event": "test"}'

    expected_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    registry = WebhookRegistry(default_secret=secret)
    assert registry.verify_signature(payload, expected_sig) is True


def test_hmac_verification_failure():
    """verify_signature returns False for an incorrect signature."""
    from app.components.inbound_webhooks.service import WebhookRegistry

    registry = WebhookRegistry(default_secret="test_secret")
    assert registry.verify_signature(b"payload", "bad_signature") is False


def test_hmac_verification_no_secret():
    """verify_signature returns False when no secret is configured."""
    from app.components.inbound_webhooks.service import WebhookRegistry

    registry = WebhookRegistry(default_secret="")
    assert registry.verify_signature(b"payload", "any_signature") is False


def test_webhook_response_schema():
    """WebhookResponse schema creates correctly."""
    from app.components.inbound_webhooks.schemas import WebhookResponse

    resp = WebhookResponse(status="received", event_id="evt_123", provider="stripe")
    assert resp.status == "received"
    assert resp.event_id == "evt_123"
    assert resp.provider == "stripe"
