# Component System

## The Registry Contract

Every activated component lives in `app/components/<name>/` and exports a `register()` function:

```python
def register(*, app: FastAPI, settings) -> None:
    """Wire this component's routers, tasks, and middleware."""
    from .api import router
    from .tasks import register_tasks
    app.include_router(router, prefix="/api/<name>")
    register_tasks(task_app)
```

## Discovery

On startup, `app/main.py` calls `_load_components()`:

1. Scans `app/components/` for subpackages with `__init__.py`
2. Checks `INSTALLED_COMPONENTS` allowlist (if set in `.env`)
3. Imports each component and calls its `register()` function
4. Logs success or failure

## Allowlist Mode

```bash
INSTALLED_COMPONENTS=smtp,stripe,webhooks
```

When set, only these components are loaded. All discovered components load when unset.

## The `app/components/` Directory

At bootstrap, `app/components/` contains only `__init__.py`. Nothing is auto-loaded until you activate a template. Activated components are copied here from `boilerplate/templates/<name>/`.
