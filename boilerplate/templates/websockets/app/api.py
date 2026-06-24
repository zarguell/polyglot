"""WebSocket API route — room-based pub/sub messaging."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.components.websockets.service import ConnectionManager

logger = structlog.get_logger()

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/api/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    """Room-based WebSocket endpoint.

    Clients connect to a named room. All messages sent by one client
    are broadcast to all other clients in the same room.
    """
    await manager.connect(websocket, room)
    logger.info("ws_client_connected", room=room)

    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(room, data, sender=websocket)
            logger.info("ws_message_broadcast", room=room)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        logger.info("ws_client_disconnected", room=room)
    except Exception:
        manager.disconnect(websocket, room)
        logger.exception("ws_error", room=room)
        raise
