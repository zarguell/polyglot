from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

CSP_BASELINE = (
    "default-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply security headers to every response."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        self._apply_headers(response, request)
        return response

    def _apply_headers(self, response: Response, request: Request) -> None:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # CSP — nonce for the HTMX CSRF bootstrap script
        nonce = getattr(request.state, "nonce", "")
        csp = f"{CSP_BASELINE}; script-src 'self' 'nonce-{nonce}'"
        response.headers["Content-Security-Policy"] = csp

        if settings.environment != "local":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
