"""Server-Sent Events endpoint for real-time ticket updates.

Uses Starlette's ``StreamingResponse`` directly (NOT ``BaseHTTPMiddleware``)
to avoid the known ASGI receive-stream consumption pitfalls.  Connected
clients are tracked in a module-level registry of ``asyncio.Queue`` objects;
``broadcast_sse_event`` pushes a message to every queue.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import structlog
from fastapi import APIRouter
from starlette.responses import StreamingResponse

from app.api.deps import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/api/sse", tags=["sse"])

# Module-level registry of connected client queues.  Each client gets its own
# queue so a slow consumer cannot block others.
_client_queues: set[asyncio.Queue[dict[str, Any]]] = set()

# Interval between SSE keep-alive comment lines.
_KEEPALIVE_SECONDS = 15


def broadcast_sse_event(data: dict[str, Any]) -> None:
    """Push an event to every connected SSE client.

    Non-blocking: if a client's queue is full the event is dropped for that
    client rather than blocking the broadcaster.
    """
    for queue in list(_client_queues):
        try:
            queue.put_nowait(data)
        except asyncio.QueueFull:
            logger.warning("sse_client_queue_full_dropping_event")


async def _event_stream(client_queue: asyncio.Queue[dict[str, Any]]) -> AsyncIterator[bytes]:
    """Yield SSE-formatted bytes: events from the queue + keep-alive comments."""
    try:
        while True:
            try:
                event = await asyncio.wait_for(
                    client_queue.get(), timeout=_KEEPALIVE_SECONDS
                )
                payload = json.dumps(event)
                yield f"data: {payload}\n\n".encode()
            except TimeoutError:
                # No event within the window; send a keep-alive comment.
                yield b": keep-alive\n\n"
    except asyncio.CancelledError:
        # Client disconnected; let the generator close cleanly.
        raise


@router.get("/tickets")
async def ticket_sse_stream(_current_user: CurrentUser) -> StreamingResponse:
    """Open an SSE stream for ticket events.

    The stream stays open until the client disconnects.  Each connected client
    receives events broadcast via :func:`broadcast_sse_event`.

    Requires an authenticated session (cookie).  Auth is validated before the
    streaming response begins.
    """

    client_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
    _client_queues.add(client_queue)

    async def _stream() -> AsyncIterator[bytes]:
        try:
            async for chunk in _event_stream(client_queue):
                yield chunk
        finally:
            _client_queues.discard(client_queue)
            logger.info("sse_client_disconnected", clients=len(_client_queues))

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable Nginx buffering
        },
    )
