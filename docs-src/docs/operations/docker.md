# Docker Compose

## Services

```yaml
services:
  postgres:   # Postgres 16 on port 5432
  app:        # FastAPI on port 8000
  worker:     # Procrastinate background worker
  mailhog:    # SMTP test server (profile: mailhog)
  pgadmin:    # DB admin UI (profile: pgadmin)
```

## Commands

```bash
make up        # Start all services
make down      # Stop all services
make logs      # Tail logs
make build     # Rebuild images
```

## Profiles

Optional services are behind Docker Compose profiles:

```bash
# With SMTP testing
docker compose --profile mailhog up -d

# With pgAdmin
docker compose --profile pgadmin up -d

# With React frontend dev server
docker compose --profile react up -d
```

## Volumes

- `pgdata` — Postgres data persisted across restarts
- Code is mounted as a bind volume in local mode for hot reloading
