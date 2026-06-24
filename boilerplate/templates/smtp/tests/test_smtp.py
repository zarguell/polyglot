"""Unit tests for SMTP component."""

from __future__ import annotations

import pytest


def test_import_smtp_component():
    """Smoke test: the component module imports cleanly."""
    import importlib

    mod = importlib.import_module("app.components.smtp")
    assert hasattr(mod, "register"), "SMTP component must expose register()"


def test_email_service_not_configured():
    """EmailService returns not_configured status when host is empty."""
    from app.components.smtp.service import EmailService

    service = EmailService(host="", port=587)
    assert service.is_configured() is False


def test_email_service_configured():
    """EmailService reports configured when host is set."""
    from app.components.smtp.service import EmailService

    service = EmailService(host="smtp.example.com", port=587, from_addr="noreply@example.com")
    assert service.is_configured() is True


def test_email_schema_validation():
    """EmailSchema validates required fields."""
    from app.components.smtp.schemas import EmailSchema

    email = EmailSchema(to="user@example.com", subject="Test", body="Hello")
    assert email.to == "user@example.com"
    assert email.subject == "Test"
    assert email.body == "Hello"


def test_email_schema_from_request():
    """EmailSchema.from_request returns a task-safe copy."""
    from app.components.smtp.schemas import EmailSchema

    original = EmailSchema(to="user@example.com", subject="Test", body="Hello")
    copy = EmailSchema.from_request(original)
    assert copy.to == original.to
    assert copy.subject == original.subject
    assert copy.body == original.body


@pytest.mark.asyncio
async def test_send_not_configured():
    """Sending without SMTP_HOST returns not_configured."""
    from app.components.smtp.service import EmailService

    service = EmailService(host="")
    result = await service.send(to="test@example.com", subject="Test", body="Hello")
    assert result["status"] == "not_configured"


@pytest.mark.asyncio
async def test_send_template_not_configured():
    """send_template without SMTP_HOST returns not_configured."""
    from app.components.smtp.service import EmailService

    service = EmailService(host="")
    result = await service.send_template(
        to="test@example.com",
        subject="Test",
        template_name="welcome.html",
        context={"name": "Test"},
    )
    assert result["status"] == "not_configured"


def test_register_is_callable():
    """register() is a callable function."""
    from app.components.smtp import register

    assert callable(register)
    assert register.__name__ == "register"
