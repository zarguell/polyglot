# Polyglot — Secure Application Boilerplate Design

**Date:** 2026-06-23
**Status:** Approved-in-principle; pending final user review
**Scope:** Full boilerplate (Milestone 1 + 11 optional templates + both frontend modes)
**Companion spec:** `docs/SPEC.md`

This document captures the design decisions, concrete tech picks, and architectural patterns that turn the SPEC into a buildable plan. The SPEC defines *what*; this design defines *how*.

---

## 1. Product identity

- **Name:** Polyglot
- **Tagline:** AI-native secure application boilerplate
- **Thesis:** A developer clones the repo, configures SSO + Postgres, runs `make up`, logs in, and lands on a safe authenticated shell. Then they drop in a PRD and an AI agent builds the real business app inside known conventions.

---

## 2. Technology picks (locked)

| Concern | Choice | Rationale |
|---|---|---|
| Language | Python 3.12 | SPEC §6.1 |
| Web framework | FastAPI (Starlette) | SPEC §6.1; middleware primitives already there |
| ORM | **SQLAlchemy 2.0 async** + asyncpg | Mature async, broad ecosystem, SPEC lists it first |
| Migrations | Alembic | SPEC §6.1 |
| Settings | pydantic-settings v2 | SPEC §6.1 |
| Auth library | Authlib (OIDC) | SPEC §6.1 |
| Sessions | Starlette `SessionMiddleware` (signed cookie) | Server-side session table for revocation/audit |
| CSRF | Custom middleware (token in session + form field + HTMX header) | Avoids extra dep; predictable behavior |
| Tasks | Procrastinate (async) | SPEC §6.1; Postgres-native |
| Templates | Jinja2 | SPEC §6.1 |
| Default frontend | HTMX 2.x + **Tailwind v4 standalone CLI** (compiled, self-hosted) + Alpine.js 3.x (SRI, optional) | Avoids Play CDN's runtime `<style>` injection (conflicts with strict CSP); Tailwind v4 standalone binary needs no Node |
| Alt frontend | React 18 + Vite + TypeScript + PostCSS Tailwind | SPEC §11.4 |
| Logging | structlog (JSON in prod, console in local) | SPEC §16.1 |
| Container | Docker Compose with profiles | SPEC §19.1 |
| Postgres | 16 (alpine) | Modern, fast, well-supported |
| Test runner | pytest + pytest-asyncio + httpx AsyncClient | Async-native |

---

## 3. Module layout

```
polyglot-stack/
├── app/
│   ├── __init__.py
│   ├── main.py                     # app factory, lifespan, middleware wiring
│   ├── api/
│   │   ├── __init__.py             # router aggregation
│   │   ├── public.py               # /, /healthz, /readyz
│   │   ├── auth.py                 # /login, /auth/callback, /logout, /me
│   │   ├── system.py               # /app (shell page), /components
│   │   └── deps.py                 # current_user, db session, audit
│   ├── core/
│   │   ├── config.py               # pydantic-settings
│   │   ├── db.py                   # async engine + sessionmaker
│   │   ├── security.py             # token hashing, secrets
│   │   ├── auth.py                 # OIDC + dev login + current_user
│   │   ├── sessions.py             # session store helpers
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── security_headers.py
│   │   │   ├── request_id.py
│   │   │   ├── structured_logging.py
│   │   │   └── csrf.py
│   │   ├── logging.py              # structlog config
│   │   ├── tasks.py                # Procrastinate App
│   │   ├── templates.py            # Jinja2 env + globals
│   │   └── errors.py               # centralized exception handlers
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── auth_session.py
│   │   ├── audit_log.py
│   │   ├── app_setting.py
│   │   ├── feature_flag.py
│   │   └── installed_component.py
│   ├── schemas/                    # Pydantic v2 I/O models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── auth.py
│   │   └── system.py
│   ├── services/                   # business logic, no HTTP/DB-impl details
│   │   ├── user_service.py
│   │   ├── audit_service.py
│   │   └── auth_service.py
│   ├── tasks/                      # Procrastinate task definitions
│   │   ├── __init__.py
│   │   └── maintenance.py          # audit log retention periodic job
│   ├── components/                 # ← activated templates live here
│   │   └── __init__.py             # registry; auto-discovers submodules
│   ├── templates/                  # Jinja2 HTML
│   │   ├── base.html
│   │   ├── public/
│   │   │   ├── home.html
│   │   │   └── login.html
│   │   ├── auth/
│   │   │   └── dev_login.html
│   │   ├── app/
│   │   │   └── shell.html
│   │   ├── errors/
│   │   │   ├── 401.html
│   │   │   ├── 403.html
│   │   │   └── 500.html
│   │   └── components/             # reusable partials
│   │       ├── nav.html
│   │       ├── user_badge.html
│   │       ├── env_badge.html
│   │       ├── flash.html
│   │       ├── card.html
│   │       ├── button.html
│   │       ├── table.html
│   │       ├── empty_state.html
│   │       └── pagination.html
│   └── static/
│       └── app.css                 # tiny custom layer over Tailwind
├── frontend/                       # React + Vite (separate compose profile)
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/client.ts
│       ├── auth/
│       ├── components/
│       └── pages/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
├── boilerplate/
│   ├── templates/                  # copy-on-activate capability packs
│   │   ├── smtp/
│   │   ├── file_storage/
│   │   ├── redis_cache/
│   │   ├── websockets/
│   │   ├── stripe/
│   │   ├── fsm_workflows/
│   │   ├── reporting_exports/
│   │   ├── inbound_webhooks/
│   │   ├── outbound_webhooks/
│   │   ├── ldap_ad/
│   │   └── django_upgrade/         # docs-only guide
│   └── frontend/
│       ├── htmx_jinja/             # reference snapshot of default frontend
│       └── react_vite/             # reference snapshot of alt frontend
├── docs/
│   ├── SPEC.md
│   ├── AGENTS.md
│   ├── DESIGN.md
│   ├── SECURITY.md
│   ├── OPERATIONS.md
│   ├── DECISIONS.md
│   └── PRD.example.md
├── tests/
│   ├── conftest.py
│   ├── factories.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/
│   ├── seed_dev.py
│   ├── activate_component.sh
│   ├── new_component.py
│   └── protonmail_oidc_mock.py     # tiny fake IdP for local dev (optional)
├── docker-compose.yml
├── docker-compose.override.yml
├── .env.example
├── .gitignore
├── pyproject.toml
├── Makefile
├── README.md
└── DESIGN_TOKENS.json              # shared design tokens (colors, type, radius)
```

---

## 4. The components-registry twist

This is the central architectural decision. SPEC §13 says templates "activate" via copying files. The naive interpretation produces awkward cross-cutting wiring (how does a copied template register its middleware? how does the worker discover its tasks?). The fix is a small, uniform contract.

### 4.1 The contract

Every activated component lives at `app/components/<name>/` and exports a `register()` function:

```python
# app/components/<name>/__init__.py
from fastapi import FastAPI
from procrastinate import App as ProcrastinateApp

def register(*, app: FastAPI, task_app: ProcrastinateApp, settings) -> None:
    """Wire this component's routers, tasks, and middleware."""
    from .api import router
    from .tasks import register_tasks
    app.include_router(router, prefix=f"/{__name__.rsplit('.', 1)[-1]}")
    register_tasks(task_app)
```

### 4.2 The registry

`app/components/__init__.py` is the only place that knows about all components:

```python
# Pseudo-code
def discover_components() -> list[str]:
    # Returns every directory under app/components/ that has __init__.py
    # Excludes registry helpers and disabled markers
    ...

def load_components(*, app, task_app, settings) -> list[str]:
    discovered = discover_components()
    allowlist = settings.installed_components  # Optional[List[str]]
    active = [c for c in discovered if not allowlist or c in allowlist]
    for name in active:
        module = importlib.import_module(f"app.components.{name}")
        if hasattr(module, "register"):
            module.register(app=app, task_app=task_app, settings=settings)
            mark_component_active(name)  # writes installed_components row
    return active
```

### 4.3 Activation semantics

When a user runs `make activate-component COMPONENT=smtp`:

1. Validate `boilerplate/templates/smtp/` exists.
2. Copy `boilerplate/templates/smtp/app/` → `app/components/smtp/`.
3. Copy `boilerplate/templates/smtp/alembic_versions/*` → `alembic/versions/`.
4. Merge `boilerplate/templates/smtp/compose.fragment.yml` into `docker-compose.override.yml`.
5. Append `boilerplate/templates/smtp/env.additions` to `.env`.
6. Optionally add name to `INSTALLED_COMPONENTS` in `.env` (if user wants allowlist mode).
7. Print next steps (run migration, restart compose, configure secrets).

### 4.4 Empty `app/components/`

At bootstrap, `app/components/` contains only `__init__.py`. Nothing is registered until the user (or AI agent) activates a template.

---

## 5. Authentication design

### 5.1 OIDC flow

Standard authorization-code flow via Authlib:

```
GET /login                → 302 to IdP authorize URL
GET /auth/callback?code=  → exchange code for tokens, validate ID token, upsert user, write audit log, set session, redirect to /app
POST /logout              → clear session cookie, invalidate auth_sessions row, audit log, redirect to /
```

### 5.2 Provider presets

Four named presets, all OIDC underneath:

| Provider key | Discovery URL | Unique claims |
|---|---|---|
| `generic` | `AUTH_OIDC_DISCOVERY_URL` (required) | Configurable via `AUTH_OIDC_*_CLAIM` env vars |
| `entra` | `https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration` | `preferred_username`, `oid` |
| `okta` | `https://{domain}/.well-known/openid-configuration` | `email`, `sub` |
| `google` | `https://accounts.google.com/.well-known/openid-configuration` | `email`, `sub` |

### 5.3 User provisioning

- First login: create user row with `is_admin=False` (unless this is the very first user — then `is_admin=True`).
- Subsequent logins: update `display_name`, `last_login_at`, write `login` audit log.
- Failed login attempts (invalid token, etc.): write `login_failed` audit log.

### 5.4 Dev login

When `AUTH_DEV_MODE=1` AND `ENVIRONMENT=local`:

- `GET /login/dev` renders a tiny form: `email`, `display_name`.
- Submitting creates a session directly (no IdP).
- Banner across the form: "DEV MODE — DO NOT USE IN PRODUCTION".
- App startup asserts `not (AUTH_DEV_MODE=1 and ENVIRONMENT=production)` and refuses to boot otherwise.

### 5.5 Session model

- Transport: Starlette `SessionMiddleware` signed cookie, name `polyglot_session`, HttpOnly, Secure in non-local, SameSite=Lax, 12h max age.
- Server-side: `auth_sessions` table with `session_token_hash`, `user_id`, `expires_at`, `ip_address`, `user_agent`, `revoked_at`.
- On every authenticated request: look up `user_id` from cookie → find unexpired, non-revoked session row → load user. Cache for 30s to avoid DB hit per request.
- Logout: set `revoked_at=now()`.

### 5.6 Roles

Two roles only at v1: `is_admin` boolean on user. Checked via `require_admin` dependency. RBAC upgrade path documented in DECISIONS.md.

---

## 6. Security defaults (locked)

### 6.1 Middleware chain (in order)

1. `RequestIdMiddleware` — injects `X-Request-ID`, sets context var for loggers.
2. `StructuredLoggingMiddleware` — logs request/response with method, path, status, latency, user_id, request_id.
3. `HTTPSRedirectMiddleware` — only when `ENVIRONMENT != local`.
4. `TrustedHostMiddleware` — `ALLOWED_HOSTS` from settings.
5. `SessionMiddleware` — see §5.5.
6. `CSRFMiddleware` — see §6.3.
7. `SecurityHeadersMiddleware` — see §6.2.
8. App routers.

### 6.2 Security headers baseline

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Strict-Transport-Security: max-age=63072000; includeSubDomains  (when HTTPS)
```

`/docs` and `/redoc` only mounted when `ENABLE_OPENAPI=1` (default false in non-local).

### 6.3 CSRF

- Token stored in session as `_csrf_token`.
- Hidden input `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` in every form.
- HTMX global header injection: small script (the only allowed inline, nonce-protected) reads token from `<meta name="csrf-token">` and sets `X-CSRFToken` on every `hx-*` request.
- Server: reject `POST/PUT/PATCH/DELETE` with missing/invalid token or header. Exempt `/auth/callback` and `/webhooks/*` (those use signature verification instead).

### 6.4 SRI for CDN assets

Self-hosted assets (Tailwind compiled CSS, app.js) need no SRI — they're same-origin under `style-src 'self'` / `script-src 'self'`.

For the few CDN assets still in use, pinned versions with integrity hashes baked into `templates/base.html`:

- `htmx.org@2.0.4`
- `alpinejs@3.14.8` (optional, opt-in via `ENABLE_ALPINE=1`)

Hashes stored in `app/core/templates.py` as constants and exposed as Jinja globals.

### 6.5 Tailwind build (replaces Play CDN)

Tailwind v4 ships a standalone `tailwindcss` binary (no Node required). Pipeline:

- `app/static/tailwind.input.css` — `@import "tailwindcss"` + any custom CSS variables from `DESIGN_TOKENS.json`
- `app/static/app.css` — compiled output (committed)
- `make watch-css` — runs `tailwindcss --watch` for local dev
- Docker compose `app-css-watcher` profile (optional) — same in container

This keeps the "no Node required for HTMX path" property of SPEC §11.3 while producing strict-CSP-compatible output.

### 6.6 Cookie rules

- All auth cookies: HttpOnly + Secure (non-local) + SameSite=Lax + bounded Max-Age.
- No wildcard `Access-Control-Allow-Origin`. Allowed origins from `CORS_ALLOWED_ORIGINS` setting (defaults to none).

---

## 7. Data model

### 7.1 Base tables (Milestone 1)

All tables in `public` schema. Procrastinate tables live in `procrastinate` schema (managed by `procrastinate schema apply`).

```sql
-- users
id              UUID PK
external_subject_id TEXT UNIQUE NOT NULL
email           CITEXT UNIQUE NOT NULL
display_name    TEXT NOT NULL
auth_provider   TEXT NOT NULL   -- 'generic' | 'entra' | 'okta' | 'google' | 'dev'
is_active       BOOL NOT NULL DEFAULT TRUE
is_admin        BOOL NOT NULL DEFAULT FALSE
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
last_login_at   TIMESTAMPTZ

-- auth_sessions
id              UUID PK
user_id         UUID FK users(id) ON DELETE CASCADE
session_token_hash TEXT UNIQUE NOT NULL
expires_at      TIMESTAMPTZ NOT NULL
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
revoked_at      TIMESTAMPTZ
ip_address      INET
user_agent      TEXT

-- audit_logs
id              UUID PK
actor_user_id   UUID FK users(id) NULL  -- null for system actions
action          TEXT NOT NULL
target_type     TEXT
target_id       TEXT
metadata        JSONB NOT NULL DEFAULT '{}'::jsonb
created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
ip_address      INET
request_id      TEXT

-- app_settings
key             TEXT PK
value           JSONB NOT NULL
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
updated_by_user_id UUID FK users(id) NULL

-- feature_flags
key             TEXT PK
enabled         BOOL NOT NULL DEFAULT FALSE
description     TEXT
updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()

-- installed_components
name            TEXT PK
version         TEXT NOT NULL
activated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
config          JSONB NOT NULL DEFAULT '{}'::jsonb
```

### 7.2 Indices

- `users` — `email`, `external_subject_id` (both unique, above).
- `auth_sessions` — `user_id`, `expires_at` partial where `revoked_at IS NULL`.
- `audit_logs` — `(actor_user_id, created_at DESC)`, `(action, created_at DESC)`.

### 7.3 JSONB usage

- `audit_logs.metadata` — genuinely irregular event data (SPEC §9.2 ✓).
- `app_settings.value` — admin-tunable config of arbitrary shape (✓).
- `installed_components.config` — per-component config (✓).
- No JSONB for users, sessions, or anything integrity-sensitive.

---

## 8. Task processing (Procrastinate)

### 8.1 App wiring

```python
# app/core/tasks.py
from procrastinate import App, AiopgConnector

task_app = App(connector=AiopgConnector())  # async psycopg pool via settings
```

### 8.2 Definitions

- `app/tasks/maintenance.py` — `audit_log_retention` periodic job (daily, prunes logs older than 90 days).
- `app/tasks/example.py` — `send_welcome_email` (logs only when SMTP not active; defers to `app.components.smtp` if present).

### 8.3 Worker service

Same image as `app`, entrypoint `procrastinate --app app.core.tasks.task_app worker --wait`. Healthcheck: process alive + can `SELECT 1` from procrastinate schema.

### 8.4 Periodic scheduling

Procrastinate periodic tasks defined in `app/tasks/__init__.py` via `@task_app.periodic(...)`. Schedule is static at v1 (no DB-driven dynamic schedules — those land with the `fsm_workflows` template).

### 8.5 Boundaries (per SPEC §10.4)

Documented in AGENTS.md. Rules of thumb:
- Job > 200ms response time → Procrastinate.
- Webhook ingestion with downstream side effects → enqueue + return 202.
- Pure read for an API response → never Procrastinate.

---

## 9. Frontend — HTMX + Jinja (default)

### 9.1 Templates

Jinja2 with autoescape on. Globals: `csrf_token()`, `current_user`, `settings`, `request`, `sri_hashes`. Base template (`templates/base.html`) wires:

```html
<!doctype html>
<html lang="en" class="h-full">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="csrf-token" content="{{ csrf_token() }}">
  <title>{% block title %}{{ settings.app_name }}{% endblock %}</title>
  <link rel="stylesheet" href="{{ static('app.css') }}">
  {% if settings.enable_alpine %}
  <script defer src="https://unpkg.com/alpinejs@3.14.8/dist/cdn.min.js"
          integrity="{{ sri('alpine') }}" crossorigin="anonymous"></script>
  {% endif %}
  <script src="https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js"
          integrity="{{ sri('htmx') }}" crossorigin="anonymous"></script>
  <script nonce="{{ request.scope['nonce'] }}">
    document.body.addEventListener('htmx:configRequest', (e) => {
      e.detail.headers['X-CSRFToken'] = document.querySelector('meta[name="csrf-token"]').content;
    });
  </script>
</head>
```

The nonce-bearing inline script is the *only* allowed inline — everything else goes through `app/static/app.js`. CSP includes `'nonce-...'` for that one script.

### 9.2 Components

Section §26 of SPEC lists required components. Each ships as a Jinja macro file under `templates/components/`:
- `nav.html` (top nav with user badge, env badge)
- `card.html`, `button.html`, `table.html`, `empty_state.html`, `pagination.html`, `flash.html`, `user_badge.html`, `env_badge.html`, `modal.html`, `form_field.html`

### 9.3 Pages

- `/` → `public/home.html` (title + login button + env badge + "shell ready" copy)
- `/login` → 302 to IdP (or render dev form if dev mode)
- `/auth/callback` → no UI, redirect
- `/app` → `app/shell.html` (user name, email, provider, health status, installed components list, "no business modules" placeholder)
- `/me` → JSON of current user
- `/logout` → POST → redirect
- Error pages: 401, 403, 404, 500 (with safe messages, no traceback)

---

## 10. Frontend — React + Vite (alt)

### 10.1 Layout

`/frontend` directory at repo root. Separate compose service `frontend-dev` (profile: `react`).

### 10.2 Stack

- Vite 5 + React 18 + TypeScript 5
- Tailwind via PostCSS (not CDN — proper build)
- `@tanstack/react-query` for server state
- `react-router` for routing
- Auth: cookie-based (same-origin). Same `polyglot_session` cookie. CORS allows `http://localhost:5173` in local only.

### 10.3 Design tokens

`DESIGN_TOKENS.json` at repo root. Both Jinja (via Jinja global) and React (via CSS variables) consume it. Single source of truth for colors, fonts, radius, density.

### 10.4 Components (mirrors §9.2)

- `AppShell`, `TopNav`, `UserBadge`, `EnvBadge`, `Card`, `Button`, `Table`, `EmptyState`, `Flash`, `Modal`, `Pagination`, `FormField`

### 10.5 Build

`npm run build` outputs to `app/static/react/` for production serving. Dev mode: Vite dev server proxies `/api` to FastAPI on port 8000.

---

## 11. Templates — copy-on-activate catalog

Each template at `boilerplate/templates/<name>/` ships:

```
<name>/
├── ACTIVATE.md           # activation steps
├── app/
│   ├── __init__.py       # exposes register()
│   ├── api.py            # FastAPI router
│   ├── service.py        # business logic
│   ├── models.py         # SQLAlchemy models (if any)
│   ├── schemas.py        # Pydantic schemas
│   ├── tasks.py          # Procrastinate task registration (if any)
│   └── templates/        # Jinja partials (if UI)
├── alembic_versions/
│   └── XXXX_<name>.py
├── tests/
│   ├── test_api.py
│   └── test_service.py
├── compose.fragment.yml
├── env.additions
└── README.md
```

### 11.1 Catalog (what each template provides)

| Template | External dep | What it does |
|---|---|---|
| `smtp` | SMTP server (Mailhog in dev) | `EmailService` + `send_email` Procrastinate task; HTML/text templates; provider-agnostic via `aiosmtplib` |
| `file_storage` | S3-compatible bucket (optional) | `Storage` protocol with local + S3 backends; upload/download endpoints |
| `redis_cache` | Redis | `aiocache` integration; cache decorators; rate limiter middleware |
| `websockets` | none | FastAPI WebSocket routes; example chat room; connection manager |
| `stripe` | Stripe API key | Stripe webhook receiver; checkout session creation; customer model |
| `fsm_workflows` | none (transitions lib) | SQLAlchemy-integrated FSM base; admin endpoints for transitions |
| `reporting_exports` | none | CSV/XLSX/PDF generation via Procrastinate; download endpoint with signed URLs |
| `inbound_webhooks` | none | Generic HMAC-signed webhook receiver registry; replay protection |
| `outbound_webhooks` | none | Outbound webhook dispatcher with retry/backoff; subscription model |
| `ldap_ad` | LDAP server | LDAP auth fallback + user directory sync (separate from OIDC primary) |
| `django_upgrade` | n/a | Docs-only migration guide (no code) |

### 11.2 Tests for external-dependent templates

All external calls go through a thin port (e.g. `EmailService.send()`, `Storage.put()`). Unit tests inject in-memory fakes. Integration tests gate on env var (e.g. `pytest.mark.integration` skipped unless `INTEGRATION_STRIPE=1`). Suite stays green without credentials.

---

## 12. Testing strategy

### 12.1 Layering

| Layer | What | Tools | Speed |
|---|---|---|---|
| Unit | services, schemas, pure logic, fakes | pytest, hypothesis | ms |
| Integration | API + DB (real Postgres test DB) | pytest-asyncio, httpx AsyncClient | ~50ms/test |
| E2E | Full stack via Docker | pytest + compose | seconds |
| Component | per-template tests | pytest | ms–s |

### 12.2 Fixtures

- `db_session` — per-test transaction, rolled back after.
- `client` — httpx AsyncClient bound to app with overridden deps.
- `auth_user` / `auth_admin` — pre-seeded user + session cookie.
- `oidc_mock` — monkeypatch Authlib to return canned ID tokens.

### 12.3 Required smoke tests (SPEC §17.1)

All present:
- auth flow (login, callback, logout, dev login)
- route smoke (every public/auth/system route returns expected status)
- middleware (security headers present, CSRF enforced, HTTPS redirect in non-local)
- DB connectivity
- worker task execution (deferring + processing via test connector)
- template rendering (every shipped template renders without errors)
- startup health (`/healthz`, `/readyz`)

### 12.4 CI

GitHub Actions:
- lint (ruff)
- typecheck (basedpyright)
- test unit + integration (with Postgres service)
- Docker build smoke

---

## 13. Configuration

### 13.1 Settings hierarchy

`pydantic-settings` reads from env (or `.env`). All settings typed:

```python
class Settings(BaseSettings):
    # App
    app_name: str = "Polyglot"
    environment: Literal["local", "dev", "staging", "production"] = "local"
    secret_key: SecretStr  # required
    enable_openapi: bool = False
    enable_alpine: bool = False

    # Database
    database_url: PostgresDsn  # required

    # Auth
    auth_dev_mode: bool = False
    auth_oidc_provider: Literal["generic", "entra", "okta", "google"] = "generic"
    auth_oidc_client_id: str | None = None
    auth_oidc_client_secret: SecretStr | None = None
    auth_oidc_discovery_url: AnyHttpUrl | None = None
    auth_oidc_tenant: str | None = None  # for entra
    auth_oidc_domain: str | None = None  # for okta
    session_max_age_seconds: int = 12 * 3600

    # Security
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    cors_allowed_origins: list[str] = []

    # Components
    installed_components: list[str] | None = None  # None = all discovered

    # Tasks
    procrastinate_schema: str = "procrastinate"

    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")
```

### 13.2 Startup asserts

Refuse to boot when:
- `environment == "production"` and `auth_dev_mode == True`
- `environment != "local"` and `secret_key` shorter than 32 bytes
- `enable_openapi == True` and `environment == "production"` (warns only — opt-in)
- `auth_oidc_provider != "generic"` and provider-specific field is missing

---

## 14. Logging

structlog with two processors:
- local: `ConsoleRenderer()` with colors
- non-local: JSON with request_id, user_id, path, status, latency

Every log entry carries `request_id` from `RequestIdMiddleware`. Worker logs carry `task_id`.

Audit log writes happen in DB *and* structured logs (dual-write). DB is canonical for query; logs are for SIEM.

---

## 15. Documentation set (SPEC §20)

| File | Owner content |
|---|---|
| `README.md` | Quick start (clone, env, SSO setup, `make up`, login), screenshots placeholder, route table |
| `SPEC.md` | Provided verbatim |
| `AGENTS.md` | Machine-operable: architecture overview, directory responsibilities, security rules, data modeling rules, task queue rules, frontend rules, testing expectations, definition of done, available templates, escalation path |
| `DESIGN.md` | User-editable design tokens; reflects `DESIGN_TOKENS.json` |
| `SECURITY.md` | Posture, defaults, deployment hardening, incident response sketch |
| `OPERATIONS.md` | Compose services, health checks, backup, restore, log shipping |
| `DECISIONS.md` | ADRs: why FastAPI, Postgres, Procrastinate, SQLAlchemy 2.0, copy-on-activate |
| `PRD.example.md` | Sample PRD (a tiny issue tracker) showing intake format |

---

## 16. Build order

Largely follows SPEC §30, expanded for full-boilerplate scope. Phased so each phase ends in a verifiable state.

1. **Repo skeleton** — pyproject, .gitignore, .env.example, Makefile stub, docs/SPEC.md committed, git init
2. **Core config + DB** — `app/core/config.py`, `db.py`, async engine, health probes, Alembic env
3. **Models + initial migration** — all §7 tables, `alembic revision --autogenerate`
4. **Security middleware** — request_id, logging, security_headers, CSRF, https_redirect (env-gated), trusted_host
5. **Auth pipeline** — OIDC, dev login, sessions, current_user dep, audit writes
6. **App shell pages + components** — base template, all UI partials, public/auth/system pages
7. **Procrastinate integration** — task_app, worker compose service, example task, periodic task
8. **Docker Compose orchestration** — postgres/app/worker + optional profiles (pgadmin, mailhog, react)
9. **Components-registry contract** — `app/components/`, registry, `activate_component.sh`
10. **Tests** — all required smoke categories green
11. **Templates (11)** — each as `boilerplate/templates/<name>/` with full structure; tests pass
12. **React + Vite frontend** — full alt frontend, compose profile
13. **Docs (AGENTS, DESIGN, SECURITY, OPERATIONS, DECISIONS, PRD.example)** — all complete
14. **README + final polish** — quick start verified end-to-end with fresh clone

---

## 17. Acceptance criteria (SPEC §27)

All must be true when complete:

- [ ] Boots locally with `make up`
- [ ] Postgres persists data across restarts
- [ ] User can log in with configured SSO (and dev login in local)
- [ ] User record upserted on login
- [ ] Authenticated shell page loads
- [ ] Worker service healthy
- [ ] Example task can be triggered and processed
- [ ] Security headers present on every response
- [ ] CSRF enforced on state-changing routes
- [ ] Tailwind/HTMX CDN assets have SRI
- [ ] Audit logs record login + logout
- [ ] All tests pass (`make test`)
- [ ] Docs explain every extension point
- [ ] All 11 templates exist with full structure and pass their own tests
- [ ] Both frontends functional (HTMX default; React via `--profile react`)

---

## 18. Known risks / open questions

- **Tailwind Play CDN in prod**: officially discouraged by Tailwind. Documented in SECURITY.md; user-tolerable for internal tools per SPEC. Production upgrade path documented (run Tailwind CLI build).
- **Procrastinate async**: uses `aiopg` connector. Works with SQLAlchemy asyncpg pool but they're separate pools. Documented in OPERATIONS.md.
- **OIDC logout (single-logout)**: not implemented in v1. Logout is app-local only. Documented as known limitation with RP-initiated logout as upgrade path.
- **CSRF on `/auth/callback`**: exempted because IdPs can't send our CSRF token; we rely on `state` parameter + PKCE for integrity.
- **CITEXT extension**: requires `CREATE EXTENSION citext`. Initial migration includes it; document in OPERATIONS.md.
- **Webhook CSRF exemption**: webhook endpoints rely on HMAC signatures, not CSRF. AGENTS.md must call this out so AI-generated webhook code includes signature verification.

---

End of design.
