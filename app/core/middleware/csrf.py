"""CSRF protection via double-submit cookie pattern.

Checks ``X-CSRFToken`` header first, falling back to the ``csrf_token`` form field.
Safe to call ``request.form()`` here because ``BodyCacheMiddleware`` (outermost)
reads and replays the request body — downstream handlers are not affected.
"""

from __future__ import annotations

import hmac
import os
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
CSRF_EXEMPT_PATHS = frozenset({
    "/auth/callback",
    "/auth/saml/acs",
    "/login/dev",          # dev-only route, always on localhost
    "/api/webhooks",        # inbound_webhooks component prefix (copy-on-activate)
    "/api/stripe/webhook",  # stripe component webhook
})


def generate_csrf_token() -> str:
    return os.urandom(32).hex()


class CSRFTokenSessionMiddleware:
    """Pure ASGI middleware that seeds ``csrf_token`` into ``scope["session"]``.

    Unlike ``BaseHTTPMiddleware`` (which wraps the scope in an internal
    ``_CachedRequest``/``Request`` proxy), this middleware operates directly
    on the ASGI ``scope`` dict — the **same** object that
    ``SessionMiddleware`` reads when serializing the response cookie.

    This guarantees the token lands in the session cookie even when the
    Jinja ``csrf_token()`` function runs inside a ``BaseHTTPMiddleware``
    ``Request`` whose scope divergence could otherwise lose the write,
    and even for responses that never render a template at all.

    **Ordering**: must be placed **inside** ``SessionMiddleware`` so that
    ``scope["session"]`` is populated before this middleware runs.
    """

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        session = scope.get("session")
        if session is not None and not session.get("csrf_token"):
            session["csrf_token"] = generate_csrf_token()

        await self.app(scope, receive, send)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie pattern: token in session, echoed by header or form field."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.method in SAFE_METHODS:
            return await call_next(request)

        if any(request.url.path.startswith(p) for p in CSRF_EXEMPT_PATHS):
            return await call_next(request)

        session_token = request.session.get("csrf_token")
        if not session_token:
            return Response("CSRF token missing from session", status_code=403)

        # Check header (set by HTMX / JS) first
        candidate = request.headers.get("X-CSRFToken", "")

        # Fall back to form field (for non-JS form submissions)
        if not candidate:
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type or \
               "multipart/form-data" in content_type:
                form = await request.form()
                candidate = form.get("csrf_token", "")

        if not candidate:
            return Response("CSRF token missing from request", status_code=403)

        if not hmac.compare_digest(session_token, candidate):
            return Response("CSRF token mismatch", status_code=403)

        return await call_next(request)
