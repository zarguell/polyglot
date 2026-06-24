# AGENTS.md — Polyglot Agent Instructions

This file is mandatory reading for any AI coding agent working on this repo.
Follow these rules unless the PRD explicitly overrides a specific point.

## Architecture Overview

Polyglot is an opinionated secure application boilerplate. It provides authentication, database, task processing, and a component system out of the box. An agent adds business logic by:

1. Reading the PRD (`docs/PRD.md`)
2. Reading this file for conventions
3. Reading `docs/DESIGN.md` for UI tokens
4. Creating domain models in `app/models/`
5. Creating API routes in `app/api/`
6. Creating UI templates in `app/templates/`
7. Writing tests
8. Creating migrations

## Directory Responsibilities

| Directory | Purpose |
|---|---|
| `app/api/` | FastAPI route handlers |
| `app/core/` | Framework-level code: config, DB, auth, middleware, tasks |
| `app/models/` | SQLAlchemy ORM models |
| `app/schemas/` | Pydantic v2 request/response schemas |
| `app/services/` | Business logic layer (no HTTP/DB-impl details) |
| `app/tasks/` | Procrastinate task definitions |
| `app/components/` | Auto-registered component modules (copied from `boilerplate/templates/`) |
| `app/templates/` | Jinja2 HTML templates (HTMX mode) |
| `app/static/` | Compiled CSS and static assets |
| `boilerplate/templates/` | Copy-on-activate component packs |
| `alembic/` | Database migrations |
| `tests/` | Test suite |
| `docs/` | Documentation |

## Security Rules (NEVER VIOLATE)

1. **No wildcard CORS** — `Access-Control-Allow-Origin: *` is forbidden in production.
2. **No inline scripts** except the CSRF bootstrap in `base.html`.
3. **All forms must include CSRF token** as hidden input and `X-CSRFToken` header for HTMX.
4. **No secrets in repo** — use `.env` or the `SECRET_KEY`/`auth_oidc_client_secret` settings.
5. **No user HTML rendered unescaped** — Jinja autoescape is on by default.
6. **All external CDN assets must use fixed versions + SRI integrity hashes.**
7. **Never add `@ts-ignore`, `@ts-expect-error`, or `as any` equivalents.**
8. **Never add wildcard `PATCH`/`DELETE` without auth checks.**
9. **Procrastinate tasks must not be used for request-local operations.**
10. **Audit log every auth-relevant event (login, logout, role change, settings change).**
11. **Webhook endpoints must use HMAC signature verification, not CSRF.**
12. **If implementing multi-tenancy, prefer service-layer tenant scoping first. RLS is defense-in-depth, not a replacement for application checks.**
13. **RLS policies must be included in Alembic migrations as ``op.execute()`` statements.**
14. **RLS requires the ``postgres`` user to enable, and each policy needs its own migration.**

## Data Modeling Rules

1. Prefer normalized tables for stable business entities.
2. Use JSONB only for genuinely dynamic fields or unstructured metadata.
3. Use explicit foreign keys for critical integrity paths.
4. Never use JSONB for ledger-like financial records by default.
5. Put per-user preferences in a structured table or constrained JSONB field.
6. All tables should have UUID primary keys.
7. All tables should have `created_at` timestamps.

## Task Queue Rules

1. Use Procrastinate for jobs longer than a normal request/response cycle (>200ms).
2. Name tasks with a prefix: `domain.action` (e.g., `billing.send_invoice`).
3. Idempotency: tasks should be safe to retry. Use `task` method retry config.
4. Don't use tasks for synchronous responses.
5. Webhook ingestion: enqueue + return 202.

## Frontend Rules

1. Default mode is HTMX + Jinja2. Use it for internal tools and CRUD.
2. React mode requires the `react` compose profile. API-first.
3. Consult `DESIGN_TOKENS.json` for colors, fonts, radius before generating UI.
4. Components folder: `app/templates/components/` for Jinja partials.
5. No bare `<script>` tags — use nonce or SRI.

## Testing Expectations

1. Each new feature needs: unit tests for business logic, integration test for API route.
2. Test against SQLite in-memory for speed.
3. Mark Postgres-only tests with `@pytest.mark.integration`.
4. Tests must pass before PR.

## Migration Workflow

1. `alembic revision --autogenerate -m "description"`
2. Review the generated migration.
3. `alembic upgrade head`
4. Commit migration alongside model changes.

## Definition of Done

- [ ] Models created/updated
- [ ] Migration generated and applied
- [ ] API routes working
- [ ] Templates render (if UI)
- [ ] Tasks defined (if background work)
- [ ] Tests pass
- [ ] No new lint/type errors
- [ ] Security rules not violated

## Available Templates

These live in `boilerplate/templates/`. Activate via `make activate-component COMPONENT=<name>`:

- `smtp` — Email sending via SMTP (requires Mailhog or real SMTP)
- `file_storage` — Local/S3 file storage
- `redis_cache` — Redis cache layer and rate limiter
- `websockets` — WebSocket connection management
- `stripe` — Stripe payment processing
- `fsm_workflows` — Finite state machine workflows
- `reporting_exports` — CSV/XLSX/PDF report generation
- `inbound_webhooks` — HMAC-signed webhook receiver
- `outbound_webhooks` — Webhook dispatch with retry
- `ldap_ad` — LDAP auth and user sync
- `django_upgrade` — Migration guide to Django (docs-only)

## Escalation Path

If requirements exceed FastAPI-first assumptions (complex admin, deep workflows, metadata-heavy systems), the path forward is documented in `docs/DECISIONS.md`. In short: FastAPI stays until Django's admin framework, FSM library, or permission system is genuinely needed.
