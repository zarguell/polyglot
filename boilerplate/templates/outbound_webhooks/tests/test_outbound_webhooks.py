"""Unit tests for Outbound Webhooks component."""

from __future__ import annotations

import importlib


def test_import_outbound_webhooks_component():
    """Smoke test: the component module imports cleanly."""
    mod = importlib.import_module("app.components.outbound_webhooks")
    assert hasattr(mod, "register"), "Outbound Webhooks component must expose register()"


def test_register_is_callable():
    """register() is a callable function."""
    from app.components.outbound_webhooks import register

    assert callable(register)
    assert register.__name__ == "register"


def test_subscription_create_schema():
    """SubscriptionCreate schema validates correctly."""
    from app.components.outbound_webhooks.schemas import SubscriptionCreate

    sub = SubscriptionCreate(
        name="my-webhook",
        url="https://example.com/hooks",
        secret="shh",
        events=["user.created", "user.updated"],
    )
    assert sub.name == "my-webhook"
    assert sub.url == "https://example.com/hooks"
    assert sub.secret == "shh"
    assert "user.created" in sub.events


def test_dispatcher_config_defaults():
    """DispatcherService applies configured defaults."""
    import os

    orig_retries = os.environ.get("WEBHOOK_MAX_RETRIES")
    orig_delay = os.environ.get("WEBHOOK_RETRY_BASE_DELAY")

    os.environ["WEBHOOK_MAX_RETRIES"] = "3"
    os.environ["WEBHOOK_RETRY_BASE_DELAY"] = "30"

    try:
        from app.components.outbound_webhooks.service import DispatcherService

        svc = DispatcherService()
        assert svc.max_retries == 3
        assert svc.base_delay == 30
    finally:
        if orig_retries is not None:
            os.environ["WEBHOOK_MAX_RETRIES"] = orig_retries
        else:
            os.environ.pop("WEBHOOK_MAX_RETRIES", None)
        if orig_delay is not None:
            os.environ["WEBHOOK_RETRY_BASE_DELAY"] = orig_delay
        else:
            os.environ.pop("WEBHOOK_RETRY_BASE_DELAY", None)


def test_dispatcher_sign():
    """_sign produces a valid HMAC-SHA256 hex digest."""
    from app.components.outbound_webhooks.service import DispatcherService

    svc = DispatcherService()
    sig = svc._sign('{"test": true}', "secret_key")
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA-256 hex


def test_dispatcher_circuit_breaker():
    """Circuit breaker trips and clears correctly."""
    from app.components.outbound_webhooks.service import DispatcherService

    svc = DispatcherService(failure_threshold=1, cooldown_seconds=100)

    url = "https://example.com/hooks"

    # Initially no circuit
    assert url not in svc._circuits

    # Trip the circuit
    svc._trip_circuit(url)
    assert url in svc._circuits

    # Clear the circuit
    svc._clear_circuit(url)
    assert url not in svc._circuits


def test_subscription_read_schema():
    """SubscriptionRead schema accepts required fields."""
    import uuid

    from app.components.outbound_webhooks.schemas import SubscriptionRead

    sub = SubscriptionRead(
        id=uuid.uuid4(),
        name="test",
        url="https://hooks.example.com",
        events=["event.a"],
        is_active=True,
        failure_count=0,
    )
    assert sub.name == "test"
    assert sub.is_active is True
