# WebSockets Component — Activation Guide

## What This Component Adds

- FastAPI WebSocket endpoint at `/api/ws/{room}` — real-time bidirectional communication
- `ConnectionManager` — room-based connection tracking (dict of room → set of WebSocket connections)
- `WSMessage` schema for structured message typing

## Prerequisites

No additional Python dependencies are required. FastAPI handles WebSocket connections natively.

## Environment Variables

No additional environment variables are needed.

## Docker Compose

No changes required. FastAPI serves WebSocket connections over the existing HTTP port.
If a reverse proxy (nginx, Caddy) is used, ensure it forwards WebSocket `Upgrade` headers.

## Migration

This component does not add database tables. Run `alembic upgrade head` to confirm.

## Verification

```bash
# Run tests
pytest tests/unit/test_websockets.py -v

# Test with wscat or websocat
wscat -c ws://localhost:8000/api/ws/room1
```

## File Layout After Activation

```
app/components/websockets/
├── __init__.py          # register() — wires the WebSocket route
├── api.py               # WebSocket endpoint at /api/ws/{room}
├── service.py           # ConnectionManager
└── schemas.py           # WSMessage
```
