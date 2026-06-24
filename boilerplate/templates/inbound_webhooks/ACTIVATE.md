# Inbound Webhooks Component — Activation Guide

## What This Component Adds

- `POST /api/webhooks/{provider}` — generic webhook receiver endpoint
- `WebhookRegistry` — maps provider names to handler functions, with HMAC-SHA256 signature verification
- `WebhookEvent` model — full payload and header logging with verification status
- `process_webhook_event` Procrastinate task — async dispatch to registered handler

## Prerequisites

No additional Python dependencies required. The component uses only `hmac` and `hashlib` from the standard library.

## Environment Variables

Add to your `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `WEBHOOK_SECRET_DEFAULT` | No | — | Shared HMAC secret for signature verification |

### Example

```bash
WEBHOOK_SECRET_DEFAULT=whsec_your_shared_secret_here
```

## Migration

This component adds the `webhook_events` table.
After activation:

```bash
make new-migration  # enter "add webhook events table"
make migrate
```

## Verification

```bash
# Run tests
pytest tests/unit/test_inbound_webhooks.py -v
```

## Registering Custom Handlers

After activation, register handlers to process webhook events:

```python
from app.components.inbound_webhooks.service import WebhookRegistry

def handle_stripe_event(event_type: str, payload: dict) -> None:
    print(f"Received {event_type}: {payload}")

registry = WebhookRegistry(default_secret="my_secret")
registry.register("stripe", handle_stripe_event)
```

Send a test webhook:

```bash
curl -X POST http://localhost:8000/api/webhooks/stripe \
  -H "Content-Type: application/json" \
  -H "x-webhook-signature: <hmac_sha256>" \
  -d '{"event": "test"}'
```

## File Layout After Activation

```
app/components/inbound_webhooks/
├── __init__.py          # register() — wires router and tasks
├── api.py               # POST /api/webhooks/{provider}
├── service.py           # WebhookRegistry, HMAC verification
├── models.py            # WebhookEvent
├── schemas.py           # WebhookResponse
└── tasks.py             # process_webhook_event
```
