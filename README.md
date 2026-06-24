# Polyglot — AI-native Secure Application Boilerplate

**Clone. Configure. Login. Then drop in a PRD and let an AI agent build your app.**

Polyglot is an opinionated starter framework for quickly generating secure internal or line-of-business applications. It runs immediately, supports login before business logic exists, and exposes clean conventions an AI agent can follow.

## Quick Start

```bash
# Prerequisites: Python 3.12+, Docker, Docker Compose

# Clone and enter
git clone <repo> && cd polyglot

# Install Python dependencies
uv sync

# Copy environment and edit
cp .env.example .env
# Set SECRET_KEY (min 32 chars) and configure OIDC or enable dev mode

# Start Postgres + App + Worker
docker compose up --build -d

# Apply migrations
make migrate

# Visit http://localhost:8000
```

## What You Get

| Feature | Status |
|---|---|
| FastAPI app | ✅ Wired |
| Postgres database | ✅ Connected |
| SSO login (OIDC) | ✅ Generic, Entra, Okta, Google |
| Authenticated shell | ✅ Dashboard page |
| Security middleware | ✅ CSP, CSRF, HSTS, security headers |
| Procrastinate worker | ✅ Running |
| Health endpoints | ✅ `/healthz`, `/readyz` |
| Audit logging | ✅ Login/logout tracked |
| Component system | ✅ Copy-on-activate templates |
| HTMX + Jinja UI | ✅ Default |
| Tests passing | ✅ Auth, security, models |
| Documentation | ✅ AGENTS, DESIGN, SECURITY, OPERATIONS, DECISIONS |

## Auth Setup

### Option A: Dev Mode (local only)

```bash
# .env
AUTH_DEV_MODE=true
ENVIRONMENT=local
```

Visit `/login` — use the dev form to sign in with any email.

### Option B: OIDC SSO

```bash
# .env — pick one provider
AUTH_OIDC_PROVIDER=entra|okta|google|generic
AUTH_OIDC_CLIENT_ID=...
AUTH_OIDC_CLIENT_SECRET=...
```

## Project Structure

```
polyglot-stack/
├── app/              # Active source code
│   ├── api/          #    Route handlers
│   ├── core/         #    Config, DB, auth, middleware
│   ├── models/       #    SQLAlchemy ORM models
│   ├── services/     #    Business logic
│   ├── tasks/        #    Procrastinate jobs
│   ├── components/   #    Self-registering modules
│   ├── templates/    #    Jinja2 HTML templates
│   └── static/       #    Compiled CSS
├── alembic/          # Database migrations
├── boilerplate/      # Copy-on-activate component packs
├── docs/             # SPEC, AGENTS, DESIGN, SECURITY, etc.
├── tests/            # Test suite
├── frontend/         # React + Vite (optional)
├── docker-compose.yml
└── Makefile
```

## Commands

| Command | Purpose |
|---|---|
| `make up` | Start all services |
| `make down` | Stop all services |
| `make logs` | Tail logs |
| `make test` | Run all tests |
| `make lint` | Lint and type-check |
| `make migrate` | Apply DB migrations |
| `make new-migration` | Generate a migration |
| `make seed` | Seed dev data |
| `make generate-tokens` | Regenerate design tokens from DESIGN_TOKENS.json |
| `make activate-component COMPONENT=<name>` | Activate a template |

## Adding Business Logic

1. Write a PRD and save it as `docs/PRD.md`
2. AI agent reads `docs/AGENTS.md` + `docs/DESIGN.md` + `docs/PRD.md`
3. Agent creates models, routes, templates, tasks, and tests
4. Agent runs migrations and verifies tests pass

## Optional Templates

Activate only what your app needs:

| Template | What it adds |
|---|---|
| `smtp` | Email sending |
| `file_storage` | File upload/download |
| `redis_cache` | Redis caching |
| `websockets` | Real-time connections |
| `stripe` | Payment processing |
| `fsm_workflows` | State machines |
| `reporting_exports` | CSV/XLSX/PDF |
| `inbound_webhooks` | Receive webhooks |
| `outbound_webhooks` | Send webhooks |
| `ldap_ad` | LDAP auth sync |

## License

MIT
