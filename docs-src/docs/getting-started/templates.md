# Template Activation

Polyglot ships 11 optional template packs in `boilerplate/templates/`. Each adds a specific capability and is activated via copy-on-activate — files are copied into `app/components/` and the component auto-registers.

## Activation Command

```bash
make activate-component COMPONENT=<name>
```

Or manually:

```bash
bash scripts/activate_component.sh <name>
```

## Available Templates

| Template | What it Adds | External Deps |
|----------|-------------|---------------|
| `smtp` | Email sending (aiosmtplib), templates, Mailhog profile | SMTP server |
| `file_storage` | File upload/download, local/S3 backends | S3 (optional) |
| `redis_cache` | Caching, rate limiter | Redis |
| `stripe` | Checkout sessions, webhooks, subscription models | Stripe API key |
| `websockets` | Real-time WebSocket connections | None |
| `fsm_workflows` | Finite state machine engine (transitions lib) | None |
| `reporting_exports` | CSV/XLSX/PDF report generation | None |
| `inbound_webhooks` | HMAC-verified webhook receiver | None |
| `outbound_webhooks` | Webhook dispatch with retry/backoff | None |
| `ldap_ad` | LDAP user directory sync | LDAP server |
| `django_upgrade` | Migration guide to Django (docs-only) | None |
| `totp_mfa` | TOTP 2FA setup, challenge, backup codes | None |

## Activation Steps

Each template's `ACTIVATE.md` documents exact steps, but the general process:

1. **Copy** — `scripts/activate_component.sh` copies source into `app/components/<name>/`
2. **Env** — Add env vars from `env.additions` to `.env`
3. **Compose** — Merge `compose.fragment.yml` into `docker-compose.override.yml`
4. **Migrate** — Copy migration files and run `alembic upgrade head`
5. **Register** — The component's `register()` function auto-wires routes and tasks

## How It Works

Each component exposes a `register()` function:

```python
def register(*, app: FastAPI, settings) -> None:
    """Wire the component's routers, tasks, and middleware."""
    from .api import router
    app.include_router(router, prefix="/api/<name>")
```

The app's component registry in `app/components/__init__.py`:

1. Discovers all subpackages in `app/components/`
2. Checks `INSTALLED_COMPONENTS` allowlist (if set)
3. Calls each active component's `register()` on startup
