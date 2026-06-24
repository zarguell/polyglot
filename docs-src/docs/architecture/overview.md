# Architecture Overview

## Thesis

PostgreSQL is the foundational infrastructure primitive. The stack evolves only when complexity genuinely requires it.

## Complexity Ladder

1. **FastAPI + Postgres** — the starting point
2. **+ Procrastinate** — background tasks and scheduled work
3. **+ Template components** — optional capability packs
4. **+ FSM/workflow libraries** — stateful orchestration
5. **+ More worker containers** — horizontal scale
6. **→ Django** — only when admin/workflow/metadata complexity justifies it

## Stack

| Layer | Choice |
|-------|--------|
| Web framework | FastAPI (Starlette) |
| ORM | SQLAlchemy 2.0 async + asyncpg |
| Migrations | Alembic |
| Auth | Authlib (OIDC + SAML) |
| Sessions | Starlette SessionMiddleware (signed cookie) |
| Task queue | Procrastinate (Postgres-backed) |
| Frontend (default) | HTMX 2 + Jinja2 + Tailwind v3 |
| Frontend (alt) | React 18 + Vite + TypeScript |
| Logging | structlog |
| Container | Docker Compose with profiles |
| Database | Postgres 16 |

## Module Layout

```
polyglot-stack/
├── app/
│   ├── api/           # Route handlers (public, auth, system, admin)
│   ├── core/          # Config, DB, auth, middleware, tasks, templates
│   ├── models/        # SQLAlchemy ORM models
│   ├── services/      # Business logic layer
│   ├── components/    # Activated template modules (auto-registered)
│   ├── templates/     # Jinja2 HTML templates
│   └── static/        # Compiled CSS
├── alembic/           # DB migrations
├── boilerplate/       # Copy-on-activate template packs
├── frontend/          # React + Vite (separate profile)
├── tests/             # pytest suite
└── docs/              # Project documentation
```

## Component System

`app/components/` is the integration point for activated templates:

```python
# app/components/__init__.py (simplified)
def load_components(app, settings):
    for name in discover_components():
        if settings.installed_components and name not in settings.installed_components:
            continue
        module = import_module(f"app.components.{name}")
        module.register(app=app, settings=settings)
```

Each component self-registers its routers, tasks, and middleware via a `register()` function. No manual wiring needed.
