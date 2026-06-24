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
