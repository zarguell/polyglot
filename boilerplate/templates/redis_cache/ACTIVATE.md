# Redis Cache Component — Activation Guide

## What This Component Adds

- `GET /api/cache/status` — returns cache hit/miss statistics
- `CacheService` — async Redis cache wrapper (redis-py async)
- `clear_cache` Procrastinate periodic task

## Prerequisites

Install additional dependencies:

```bash
uv add redis
```

## Environment Variables

Add to your `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis connection URL |

### Example

```bash
REDIS_URL=redis://redis:6379/0
```

## Docker Compose

Add the `redis` service to your compose setup. The fragment below provides a
basic Redis container. Merge it into `docker-compose.override.yml` or keep it
in `docker-compose.yml`.

## Migration

This component does not add database tables. Run `alembic upgrade head` to confirm.

## Verification

```bash
# Run tests
pytest tests/unit/test_redis_cache.py -v

# Check cache status via API
curl http://localhost:8000/api/cache/status
```

## File Layout After Activation

```
app/components/redis_cache/
├── __init__.py          # register() — wires router and tasks
├── api.py               # GET /api/cache/status
├── service.py           # CacheService
└── tasks.py             # clear_cache periodic task
```
