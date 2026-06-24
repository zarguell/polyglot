# SMTP Component — Activation Guide

## What This Component Adds

- `POST /api/email/test` — send a test email (authenticated)
- `EmailService` — async email sending via aiosmtplib with Jinja2 templates
- `send_email` Procrastinate task with retry support
- `EmailSchema` for validation
- Email templates in `app/templates/email/` (welcome, base)

## Prerequisites

Install additional dependencies:

```bash
uv add aiosmtplib
```

## Environment Variables

Add to your `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `SMTP_HOST` | Yes | — | SMTP server hostname |
| `SMTP_PORT` | Yes | — | SMTP server port |
| `SMTP_USER` | No | — | SMTP username for auth |
| `SMTP_PASSWORD` | No | — | SMTP password for auth |
| `SMTP_USE_TLS` | No | `true` | Use TLS encryption |
| `EMAIL_FROM` | Yes | — | Default From address |

### Example (MailHog for development)

```bash
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USE_TLS=false
EMAIL_FROM=noreply@polyglot.local
```

### Example (production)

```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.your-api-key
SMTP_USE_TLS=true
EMAIL_FROM=noreply@yourdomain.com
```

## Docker Compose

MailHog is available in `docker-compose.override.yml` under the `mailhog` profile.
You do NOT need to add a `mailhog` service to `compose.fragment.yml` — it is already
in the override file. Start it with:

```bash
docker compose --profile mailhog up -d
```

Access the MailHog web UI at http://localhost:8025

## Migration

This component does not add database tables. Run `alembic upgrade head` anyway
to confirm no pending migrations exist.

## Verification

```bash
# Start MailHog
docker compose --profile mailhog up -d

# Run tests
pytest tests/unit/test_smtp.py -v

# Send a test email via API (requires auth)
curl -X POST http://localhost:8000/api/email/test \
  -H "Content-Type: application/json" \
  -d '{"to": "test@example.com", "subject": "Test", "body": "Hello"}'
```

## File Layout After Activation

```
app/components/smtp/
├── __init__.py          # register() — wires router and tasks
├── api.py               # POST /api/email/test
├── service.py           # EmailService
├── tasks.py             # send_email Procrastinate task
├── schemas.py           # EmailSchema
└── templates/
    └── email/
        ├── base_email.html
        └── welcome.html
```
