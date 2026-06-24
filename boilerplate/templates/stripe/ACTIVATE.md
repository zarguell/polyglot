# Stripe Component — Activation Guide

## What This Component Adds

- `POST /api/stripe/checkout` — create a Stripe Checkout session (authenticated)
- `POST /api/stripe/webhook` — receive Stripe webhooks (signature-verified)
- `StripeService` — wraps the Stripe Python SDK
- `StripeCustomer` model — links Polyglot users to Stripe customer IDs
- `StripeSubscription` model — tracks active subscriptions
- `StripeEvent` model — idempotent webhook event log
- `sync_stripe_customer` Procrastinate task
- `handle_stripe_event` Procrastinate task

## Prerequisites

Install additional dependencies:

```bash
uv add stripe
```

## Environment Variables

Add to your `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `STRIPE_SECRET_KEY` | Yes | — | Stripe secret key (starts with `sk_`) |
| `STRIPE_WEBHOOK_SECRET` | Yes | — | Stripe webhook signing secret (starts with `whsec_`) |
| `STRIPE_PRICE_ID` | No | — | Default price ID for checkout sessions |

### Example

```bash
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
```

## Stripe CLI (local testing)

Use Stripe CLI to forward webhooks to your local server:

```bash
stripe listen --forward-to localhost:8000/api/stripe/webhook
```

## Migration

This component adds tables: `stripe_customers`, `stripe_subscriptions`, `stripe_events`.
After activation:

```bash
make new-migration  # enter "add stripe tables"
make migrate
```

## Verification

```bash
# Run tests
pytest tests/unit/test_stripe.py -v
```

## File Layout After Activation

```
app/components/stripe/
├── __init__.py          # register() — wires router and tasks
├── api.py               # POST checkout, POST webhook
├── service.py           # StripeService
├── models.py            # StripeCustomer, StripeSubscription, StripeEvent
├── schemas.py           # CheckoutRequest, CheckoutResponse
└── tasks.py             # sync_stripe_customer, handle_stripe_event
```
