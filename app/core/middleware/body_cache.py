"""BodyCacheMiddleware — reads the ASGI request body once and replays it.

Starlette's ``BaseHTTPMiddleware`` creates a **new ``Request`` object per layer**,
each backed by the same ASGI ``receive`` stream.  When any middleware calls
``request.body()`` or ``request.form()`` the underlying stream is consumed,
leaving downstream handlers with an empty body and **no error or warning**.

This middleware runs **before** any ``BaseHTTPMiddleware`` wrapper.  It reads the
full body from the original ``receive``, caches it, and replaces the ``receive``
callable with one that replays the cached bytes on every call.  This way every
subsequent ``Request`` (from any middleware or route handler) gets the full body
as if it was never consumed.

**Ordering**: must be the outermost middleware (added last, called first inbound),
so it wraps everything else.  Already guaranteed by its position in ``main.py``.
"""
from __future__ import annotations

from typing import Any


class BodyCacheMiddleware:
    """Raw ASGI middleware: caches request body, replays via patched receive."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Read the full body from the original receive stream
        chunks: list[bytes] = []
        more_body = True
        while more_body:
            msg = await receive()
            if msg["type"] == "http.request":
                chunks.append(msg.get("body", b""))
                more_body = msg.get("more_body", False)

        body = b"".join(chunks)

        # Build a receive that ALWAYS returns the full cached body.
        # Each BaseHTTPMiddleware layer creates a new Request object, and each
        # Request calls this receive independently.  Using a one-shot iterator
        # would only serve the first consumer — subsequent consumers (other
        # middleware layers, the route handler) would get an empty body.
        async def cached_receive() -> dict:
            return {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }

        await self.app(scope, cached_receive, send)
