"""Unit tests for WebSockets component."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock


def test_import_websockets_component():
    """Smoke test: the component module imports cleanly."""
    import importlib

    mod = importlib.import_module("app.components.websockets")
    assert hasattr(mod, "register"), "WebSockets component must expose register()"


def test_connection_manager_initial_state():
    """ConnectionManager starts with no rooms and no connections."""
    from app.components.websockets.service import ConnectionManager

    mgr = ConnectionManager()
    assert mgr.active_rooms == []
    assert mgr.active_connections == 0


def test_connection_manager_disconnect_cleans_up():
    """Disconnecting the last client removes the room."""
    from app.components.websockets.service import ConnectionManager

    mgr = ConnectionManager()
    mock_ws = AsyncMock()

    # Simulate adding a connection without actually calling accept()
    mgr._rooms["test-room"] = {mock_ws}

    assert "test-room" in mgr._rooms
    mgr.disconnect(mock_ws, "test-room")
    assert "test-room" not in mgr._rooms


def test_connection_manager_broadcast_skips_sender():
    """broadcast does not send back to the originating websocket."""
    from app.components.websockets.service import ConnectionManager

    mgr = ConnectionManager()
    sender = AsyncMock()
    receiver = AsyncMock()
    mgr._rooms["room"] = {sender, receiver}

    async def _run():
        await mgr.broadcast("room", "hello", sender=sender)
        sender.send_text.assert_not_called()
        receiver.send_text.assert_called_with("hello")

    asyncio.run(_run())


def test_ws_message_schema():
    """WSMessage carries type, payload, sender, and timestamp."""
    from app.components.websockets.schemas import WSMessage

    msg = WSMessage(type="chat", payload="Hello world", sender="user123")
    assert msg.type == "chat"
    assert msg.payload == "Hello world"
    assert msg.sender == "user123"
    assert msg.timestamp is not None


def test_ws_message_default_type():
    """WSMessage default type is 'message'."""
    from app.components.websockets.schemas import WSMessage

    msg = WSMessage(payload="test")
    assert msg.type == "message"


def test_register_is_callable():
    """register() is a callable function."""
    from app.components.websockets import register

    assert callable(register)
    assert register.__name__ == "register"
