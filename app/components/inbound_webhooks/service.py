"""WebhookRegistry — maps provider names to handlers with HMAC verification."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable
from typing import Any

import structlog

logger = structlog.get_logger()

HandlerFunc = Callable[[str, dict[str, Any]], None]


class WebhookRegistry:
    """Registry mapping provider names to handler functions.

    Supports HMAC-SHA256 signature verification with a shared secret.
    """

    def __init__(self, default_secret: str = "") -> None:
        self._handlers: dict[str, HandlerFunc] = {}
        self._default_secret = default_secret

    def register(self, provider: str, handler: HandlerFunc) -> None:
        """Register a handler for a provider."""
        self._handlers[provider] = handler
        logger.info("webhook_handler_registered", provider=provider)

    def get_handler(self, provider: str) -> HandlerFunc | None:
        """Look up the handler for a given provider."""
        return self._handlers.get(provider)

    def verify_signature(self, payload: bytes, signature: str, secret: str = "") -> bool:
        """Verify an HMAC-SHA256 signature against the payload.

        Uses the provided secret or falls back to the default secret.
        """
        key = (secret or self._default_secret).encode()
        if not key:
            return False

        expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def list_providers(self) -> list[str]:
        """Return registered provider names."""
        return list(self._handlers.keys())


# Module-level shared singleton.  Both the API layer and the background task
# dispatcher resolve handlers through this instance so that providers
# registered at startup (or in the worker via task discovery) are visible to
# ``process_webhook_event``.
_registry_singleton: WebhookRegistry | None = None


def get_webhook_registry() -> WebhookRegistry:
    """Return the process-wide :class:`WebhookRegistry` singleton.

    Lazily created with the default secret from settings.  Domain handlers
    (e.g. ``email`` → ticket creation) are registered on this instance by
    their owning modules at import/startup time.
    """
    global _registry_singleton
    if _registry_singleton is None:
        from app.core.config import settings

        _registry_singleton = WebhookRegistry(default_secret=settings.webhook_secret_default)
    return _registry_singleton
