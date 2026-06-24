"""Procrastinate task_app and periodic task definitions.

Usage:
    @task_app.task(name="domain.action")
    def my_task(...):
        ...

    # Periodic triggers must wrap an already-registered task (Procrastinate 2.6+ API).
    periodic_my_task = task_app.periodic(
        cron="0 * * * *",
        task_name="domain.action",
    )(my_task)
"""

from __future__ import annotations

from datetime import UTC

import structlog
from procrastinate import App
from procrastinate.contrib.aiopg import AiopgConnector

from app.core.config import settings

logger = structlog.get_logger()

# Build async connection string without +asyncpg suffix for Procrastinate
dsn = str(settings.database_url).replace("+asyncpg", "")

task_app = App(connector=AiopgConnector(dsn=dsn))


@task_app.task(name="example.hello_world")
def hello_world(name: str = "World") -> None:
    """Example task that logs and returns."""
    logger.info("task_executed", task_name="hello_world", name=name)


@task_app.task(name="maintenance.audit_log_retention")
def audit_log_retention(retention_days: int = 90) -> None:
    """Periodic task: prune old audit logs. Runs daily."""
    import asyncio
    from datetime import datetime, timedelta

    from app.core.db import async_session_factory
    from app.models.audit_log import AuditLog

    async def _prune():
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        async with async_session_factory() as db:
            from sqlalchemy import delete

            await db.execute(
                delete(AuditLog).where(AuditLog.created_at < cutoff),
            )
            await db.commit()
            logger.info("audit_log_pruned", cutoff=cutoff.isoformat())

    asyncio.run(_prune())


# Procrastinate 2.6+: periodic() wraps an already-registered task (has .name attr).
# The old pattern of decorating a plain wrapper function no longer works.
periodic_audit_log_retention = task_app.periodic(
    cron="0 3 * * *",
    task_name="maintenance.audit_log_retention",
)(audit_log_retention)


def _register_components() -> None:
    """Call ``register()`` on each installed component for the worker process.

    Mirrors ``app.main._load_components`` but for the Procrastinate worker.
    The worker has no FastAPI application, so ``app`` is passed as ``None``;
    component ``register()`` functions guard route registration behind
    ``if app is not None`` while still executing process-global side effects
    (task handler registration, registry hooks, etc.).

    Without this, handlers wired inside ``component/__init__.py:register()``
    are available in the web process but silently missing in the worker.
    """
    import importlib
    import pkgutil

    import app.components as components_pkg

    discovered = [
        name
        for _, name, is_pkg in pkgutil.iter_modules(components_pkg.__path__)
        if is_pkg and name != "__init__"
    ]

    active = discovered
    if settings.installed_components is not None:
        active = [c for c in discovered if c in settings.installed_components]

    for name in active:
        try:
            module = importlib.import_module(f"app.components.{name}")
            if hasattr(module, "register"):
                module.register(app=None, settings=settings)
                logger.info("worker_component_registered", name=name)
        except Exception:
            logger.exception("worker_component_register_failed", name=name)
            raise


def _discover_task_modules() -> None:
    """Import every module under ``app.tasks`` so task decorators register.

    Procrastinate tasks register via the side effect of importing a module that
    contains ``@task_app.task(...)``.  Without auto-discovery a developer must
    remember to add ``import app.tasks.foo`` somewhere; forgetting that makes
    the task silently absent from the worker with no error.

    Scanning ``app/tasks/`` and importing each module removes that footgun: drop
    a ``.py`` file in, and it is registered automatically.  Import failures are
    *not* swallowed — a broken task module fails loudly at worker/app startup
    instead of vanishing silently.  This mirrors the component auto-discovery in
    ``app.main._load_components``.
    """
    import importlib
    import pkgutil

    import app.tasks as tasks_pkg

    for _finder, name, _is_pkg in pkgutil.iter_modules(tasks_pkg.__path__):
        if name == "__init__":
            continue
        importlib.import_module(f"app.tasks.{name}")
        logger.debug("task_module_imported", module=name)


# Register component hooks (handler registries, task imports) before
# discovering task modules — some task modules depend on handlers registered
# by component register() hooks.
_register_components()

# Import all task modules so their @task_app.task decorators run as a side
# effect.  This runs after ``task_app`` is defined above, so modules that do
# ``from app.core.tasks import task_app`` resolve correctly.
_discover_task_modules()
