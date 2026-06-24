"""CSRF protection via double-submit cookie pattern.

Checks ``X-CSRFToken`` header first, falling back to ``csrf_token`` form field
(via manual body parsing).  Caches the raw body in ``scope["_cached_body"]`` so
downstream route handlers can re-read it without losing data to BaseHTTPMiddleware's
per-layer Request creation.
"""

from __future__ import annotations

import hmac
import os
from urllib.parse import parse_qs

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
CSRF_EXEMPT_PATHS = frozenset({"/auth/callback", "/auth/saml/acs", "/webhooks"})


def generate_csrf_token() -> str:
    return os.urandom(32).hex()


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie pattern: token in session, echoed by header or form field.

    ⚠️  Starlette's ``BaseHTTPMiddleware`` creates a **new Request object per layer**,
    which means ``request.form()`` or ``request.body()`` called in this middleware
    silently consumes the ASGI receive stream for downstream handlers.

    To prevent silent data loss, this middleware:
    1. Reads the raw body via ``request.body()`` (parsing the CSRF token manually)
    2. Caches the raw bytes in ``scope["_cached_body"]``
    3. Downstream route handlers check ``scope.get("_cached_body")`` before calling
       ``request.body()`` / ``request.form()`` themselves
    """

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

        # 1. Check header (set by HTMX or JavaScript)
        candidate = request.headers.get("X-CSRFToken", "")

        # 2. Check form body only if header wasn't present
        #    Use manual body parsing so the body bytes can be cached for downstream.
        if not candidate:
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type:
                raw_body = await request.body()
                request.scope["_cached_body"] = raw_body
                try:
                    params = parse_qs(raw_body.decode())
                    form_token = params.get("csrf_token", [None])[0]
                    candidate = form_token or ""
                except Exception:
                    pass
            elif "multipart/form-data" in content_type:
                raw_body = await request.body()
                request.scope["_cached_body"] = raw_body

        if not candidate:
            return Response(
                "CSRF token missing from request", status_code=403
            )

        if not hmac.compare_digest(session_token, candidate):
            return Response("CSRF token mismatch", status_code=403)

        return await call_next(request)
