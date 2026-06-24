# OPERATIONS.md — Polyglot Operations Guide

## Docker Compose Services

### Required services

| Service | Image | Port | Health Check |
|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | `pg_isready` |
| `app` | polyglot-app (build) | 8000 | `/healthz` |
| `worker` | polyglot-app (same image) | — | process liveness |

### Optional profiles

| Profile | Service | Port | Activation |
|---|---|---|---|
| `mailhog` | mailhog/mailhog | 8025, 1025 | `docker compose --profile mailhog up` |
| `pgadmin` | dpage/pgadmin4 | 5050 | `docker compose --profile pgadmin up` |

## Health Checks

- `/healthz` — always returns 200 if the app is running
- `/readyz` — returns 200 when DB is reachable, 503 otherwise
- Postgres health check runs every 10s during startup

## Backup

Postgres volume is named `pgdata`. Backup with:

```bash
docker compose exec postgres pg_dump -U polyglot -d polyglot > backup.sql
```

## Restore

```bash
cat backup.sql | docker compose exec -T postgres psql -U polyglot -d polyglot
```

## Migration Commands

- `make migrate` — apply pending migrations
- `make new-migration` — autogenerate a migration (prompts for message)
- Migrations run in the `alembic` container or locally via Python

## Logs

- App logs: `docker compose logs -f app`
- Worker logs: `docker compose logs -f worker`
- JSON format in non-local environments

## Environment Separation

| Env | `ENVIRONMENT` | HTTPS | DB | Auth |
|---|---|---|---|---|
| Local | `local` | No | localhost | OIDC or Dev |
| Dev | `dev` | Recommended | dev/staging | OIDC required |
| Staging | `staging` | Yes | staging | OIDC required |
| Production | `production` | Yes (proxy) | production | OIDC required, no dev mode |

## Procrastinate

The worker connects to Postgres using the same `DATABASE_URL`. Procrastinate uses its own schema (`procrastinate` by default) for task state.

To manually inspect:
```bash
docker compose exec postgres psql -U polyglot -d polyglot -c "SELECT * FROM procrastinate_jobs LIMIT 10;"
```

## Tailwind Build

HTMX mode uses Tailwind v4 compiled CSS. Run `make watch-css` during development. Production: pre-build in Dockerfile.
