"""ConnectionManager — track WebSocket connections per room."""

from __future__ import annotations

from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections grouped by room.

    Each room is a dict key mapping to a set of WebSocket connections.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str) -> None:
        """Accept a WebSocket connection and add to the room."""
        await websocket.accept()
        if room not in self._rooms:
            self._rooms[room] = set()
        self._rooms[room].add(websocket)

    def disconnect(self, websocket: WebSocket, room: str) -> None:
        """Remove a WebSocket connection from the room."""
        if room in self._rooms:
            self._rooms[room].discard(websocket)
            if not self._rooms[room]:
                del self._rooms[room]

    async def broadcast(self, room: str, message: str, sender: WebSocket) -> None:
        """Send a message to all connections in a room except the sender."""
        if room not in self._rooms:
            return
        for connection in self._rooms[room].copy():
            if connection != sender:
                await connection.send_text(message)

    async def send_personal(self, message: str, websocket: WebSocket) -> None:
        """Send a message to a single connection."""
        await websocket.send_text(message)

    @property
    def active_rooms(self) -> list[str]:
        """Return the list of rooms with active connections."""
        return list(self._rooms.keys())

    @property
    def active_connections(self) -> int:
        """Return the total number of active connections across all rooms."""
        return sum(len(conns) for conns in self._rooms.values())
