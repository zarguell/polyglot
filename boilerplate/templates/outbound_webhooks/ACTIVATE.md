# Outbound Webhooks Component — Activation Guide

## What This Component Adds

- `POST /api/webhook-subscriptions` — create a new webhook subscription
- `GET /api/webhook-subscriptions` — list all subscriptions
- `GET /api/webhook-subscriptions/{id}` — get a single subscription
- `POST /api/webhook-subscriptions/{id}/test` — send a test webhook
- `DispatcherService` — HTTP dispatch with retry, exponential backoff, and circuit breaker
- `WebhookSubscription` model — subscriber registration and health tracking
- `WebhookDelivery` model — per-attempt delivery audit log
- `dispatch_webhook` Procrastinate task — async webhook dispatch with backoff

## Prerequisites

Install additional dependencies:

```bash
uv add httpx
```

## Environment Variables

Add to your `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `WEBHOOK_MAX_RETRIES` | No | `5` | Max retry attempts per delivery |
| `WEBHOOK_RETRY_BASE_DELAY` | No | `60` | Base delay in seconds for exponential backoff |

### Example

```bash
WEBHOOK_MAX_RETRIES=5
WEBHOOK_RETRY_BASE_DELAY=60
```

## Migration

This component adds tables: `webhook_subscriptions`, `webhook_deliveries`.
After activation:

```bash
make new-migration  # enter "add outbound webhooks tables"
make migrate
```

## Verification

```bash
# Run tests
pytest tests/unit/test_outbound_webhooks.py -v
```

## Quick Start

```python
from app.components.outbound_webhooks.service import DispatcherService
import asyncio

async def main():
    svc = DispatcherService(max_retries=3, base_delay=10)
    status, code, body = await svc.dispatch(
        url="https://webhook.site/your-uuid",
        secret="my_shared_secret",
        event_type="user.created",
        payload={"user_id": "abc", "email": "alice@example.com"},
    )
    print(f"Delivery: {status} (HTTP {code})")

asyncio.run(main())
```

## File Layout After Activation

```
app/components/outbound_webhooks/
├── __init__.py          # register() — wires router and tasks
├── api.py               # CRUD + POST test endpoint
├── service.py           # DispatcherService (retry, backoff, circuit breaker)
├── models.py            # WebhookSubscription, WebhookDelivery
├── schemas.py           # SubscriptionCreate, SubscriptionRead
└── tasks.py             # dispatch_webhook
```
