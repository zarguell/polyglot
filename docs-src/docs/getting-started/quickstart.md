# Quick Start

## Prerequisites

- Python 3.12+
- Docker + Docker Compose
- `uv` (Python package manager)

## Clone and Setup

```bash
git clone https://github.com/zarguell/polyglot.git
cd polyglot
cp .env.example .env
```

Edit `.env` and set at minimum:

```bash
SECRET_KEY=your-32-char-random-string-here
ENVIRONMENT=local
AUTH_DEV_MODE=true      # enables dev login (no SSO config needed)
```

## Start the Stack

```bash
docker compose up --build -d
```

This starts:

- **Postgres 16** on port 5432
- **App** (FastAPI + Uvicorn) on port 8000
- **Worker** (Procrastinate) for background tasks

## Apply Migrations

```bash
docker compose exec app alembic upgrade head
```

## Visit the App

| Page | URL |
|------|-----|
| Home | [http://localhost:8000](http://localhost:8000) |
| Dev Login | [http://localhost:8000/login](http://localhost:8000/login) |
| Health | [http://localhost:8000/healthz](http://localhost:8000/healthz) |
| API Docs | [http://localhost:8000/docs](http://localhost:8000/docs) |

## Create Your First User

1. Navigate to [http://localhost:8000/login](http://localhost:8000/login)
2. Enter an email and display name
3. Click **Sign in (Dev)**
4. You'll land on the dashboard — you're now authenticated as admin

## Next Steps

- Read [Configuration](configuration.md) for environment variables
- Set up [real SSO](auth-setup.md) with OIDC or SAML
- Explore [available templates](templates.md) you can activate
- Drop a `docs/PRD.md` into the repo and let an AI agent build your business logic
