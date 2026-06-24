# AGENTS.md — Polyglot Agent Instructions

This file is mandatory reading for any AI coding agent working on this repo.
Follow these rules unless the PRD explicitly overrides a specific point.

---

## Quick Reference (use these patterns)

### New Model
```python
# app/models/my_entity.py
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import AuditMixin, Base, uuid_pk

class MyEntity(AuditMixin, Base):
    __tablename__ = "my_entities"
    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
```

### New Route (HTML form handler — always use manual body parsing)
```python
# app/api/my_routes.py
from __future__ import annotations
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from app.api.deps import CurrentUser, DbDeps
from app.core.errors import NotFoundError
from app.core.templates import get_jinja_env
from app.services.my_service import create_entity, get_entities

router = APIRouter(tags=["my_entities"])

@router.get("/my-entities", response_class=HTMLResponse)
async def list_page(request: Request, user: CurrentUser, db: DbDeps):
    items = await get_entities(db, user.id)
    env = get_jinja_env()
    return HTMLResponse(
        env.get_template("my_entities/list.html").render(
            request=request, user=user, items=items
        )
    )
```

### New Route (form POST — body-safe pattern)
```python
# Always parse form data manually to avoid Starlette body-consumption issues.
# The CSRF middleware caches the raw body in scope["_cached_body"].
from urllib.parse import parse_qs

@router.post("/my-entities")
async def create_form(request: Request, user: CurrentUser, db: DbDeps):
    raw = request.scope.get("_cached_body") or await request.body()
    form = parse_qs(raw.decode()) if raw else {}
    # form is now a dict of {key: [value, ...]}
    name = form.get("name", [""])[0]
    ...
```

### New Service
```python
# app/services/my_service.py
from __future__ import annotations
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.my_entity import MyEntity

async def create_entity(db: AsyncSession, user_id: uuid.UUID, *, name: str) -> MyEntity:
    entity = MyEntity(user_id=user_id, name=name)
    db.add(entity)
    await db.flush()
    return entity
```

### New Task (with periodic trigger)
```python
# app/tasks/my_tasks.py
from app.core.tasks import task_app

@task_app.task(name="my_app.my_action")
def my_action(param: str = "") -> None:
    import asyncio
    ...

# Periodic trigger: wraps the already-registered task (Procrastinate 2.6+ API).
# Do NOT use @task_app.periodic() as a decorator on a plain function.
periodic_my_action = task_app.periodic(
    cron="0 * * * *",
    task_name="my_app.my_action",
)(my_action)
```

### New Template (extends base.html)
```jinja
{% extends "base.html" %}
{% block title %}{{ app_name }} — Page Title{% endblock %}
{% block nav %}{% include "components/nav.html" %}{% endblock %}
{% block content %}
<div class="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
  <h1 class="text-2xl font-bold">Page Title</h1>
  ...
</div>
{% endblock %}
```

---

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
9. **Running `make smoke-test` to verify the app boots**

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
6. **Periodic triggers**: use the wrapper pattern (see Quick Reference). Do NOT use `@task_app.periodic()` as a decorator on a plain function — Procrastinate 2.6+ requires the target to be a registered task.

## Frontend Rules

1. Default mode is HTMX + Jinja2. Use it for internal tools and CRUD.
2. React mode requires the `react` compose profile. API-first.
3. Consult `DESIGN_TOKENS.json` for colors, fonts, radius before generating UI.
4. Components folder: `app/templates/components/` for Jinja partials.
5. No bare `<script>` tags — use nonce or SRI.

## Critical Traps (read these before writing any code)

### Trap 1: Form body silently consumed by middleware

Starlette's `BaseHTTPMiddleware` creates a new `Request` object per middleware layer.
If any middleware calls `request.form()` or `request.body()`, it **consumes the ASGI
receive stream** — downstream handlers get an empty body with no error or warning.

**Always use this pattern in route handlers that receive form data:**
```python
raw = request.scope.get("_cached_body") or await request.body()
form = parse_qs(raw.decode()) if raw else {}
```

The CSRF middleware caches the body bytes in `scope["_cached_body"]` after it reads
them. Check the cache first; fall back to `request.body()`.

### Trap 2: Procrastinate periodic() decorator

`@task_app.periodic(cron="...")` on a plain function wrapper **no longer works**
in Procrastinate 2.6+. The function must be a registered task first. Always use
the wrapper pattern shown in the Quick Reference.

### Trap 3: Session cookie name is derived, not hardcoded

The cookie name comes from `settings.app_name` via `SESSION_COOKIE_NAME` in
`app/main.py`. **Never hardcode `"polyglot_session"`** in tests or middleware.
Import `SESSION_COOKIE_NAME` from `app.main` instead.

### Trap 4: Audit event listener fires for ALL Base subclasses

Models that extend `Base` directly (without `AuditMixin`) will crash on
insert/update because the audit listener tries to set `created_by_user_id`.
Either add `AuditMixin` to your model or ensure it has the audit columns.

## Testing Expectations

1. Each new feature needs: unit tests for business logic, integration test for API route.
2. **Tests run against Postgres in Docker** (via `make test`). SQLite is not used —
   `func.now()` returns offset-naive datetimes on SQLite but offset-aware on Postgres,
   causing silent template rendering crashes.
3. Never use PostgreSQL-only types (`ARRAY`, `JSONB`) unless you're running
   integration tests against Postgres. Prefer `JSON` (cross-DB compatible).
4. Tests must pass before PR.

## Migration Workflow

1. `alembic revision --autogenerate -m "description"`
2. Review the generated migration.
3. `alembic upgrade head`
4. Commit migration alongside model changes.

## Guard Rails (machine-enforced conventions)

These Makefile targets verify conventions. Run them before every push.

```bash
make pre-commit        # lint + test + smoke-test + check-deps + verify-tasks
make smoke-test        # verify the app boots, pages render, headers present
make check-deps        # verify all app modules import without errors
make verify-tasks      # verify all task modules register without errors
```

| Guard rail | What it enforces | What it catches |
|---|---|---|
| `make smoke-test` | App boots, pages render, CSRF works | Silent body drops, Procrastinate API drift, missing deps |
| `make check-deps` | All modules import | Missing transitive deps (aiopg, psycopg-binary) |
| `make verify-tasks` | Task registration | `periodic()` syntax errors |
| `make lint` | Code style, types | `os.getenv` outside config, type errors |
| `make test` | Tests pass | Logic errors, model/schema/routes broken |

## Definition of Done

- [ ] Models created/updated
- [ ] Migration generated and applied
- [ ] API routes working
- [ ] Templates render (if UI)
- [ ] Tasks defined (if background work)
- [ ] Tests pass (`make test`)
- [ ] Lint and type-check pass (`make lint`)
- [ ] Guard rails pass (`make pre-commit` or individually `make smoke-test check-deps verify-tasks`)
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
