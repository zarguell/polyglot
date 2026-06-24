from __future__ import annotations

import hmac
import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
CSRF_EXEMPT_PATHS = frozenset({"/auth/callback", "/webhooks"})


def generate_csrf_token() -> str:
    return os.urandom(32).hex()


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie pattern: token in session, echoed by form or header."""

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

        header_token = request.headers.get("X-CSRFToken", "")
        form_token = (
            (await request.form()).get("csrf_token", "")
            if request.headers.get("content-type", "").startswith(
                "multipart/form-data",
            )
            | request.headers.get("content-type", "").startswith(
                "application/x-www-form-urlencoded",
            )
            else ""
        )

        candidate = header_token or form_token
        if not candidate:
            return Response("CSRF token missing from request", status_code=403)

        if not hmac.compare_digest(session_token, candidate):
            return Response("CSRF token mismatch", status_code=403)

        return await call_next(request)
