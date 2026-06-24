"""Procrastinate task modules.

Modules in this package are imported automatically by
``app.core.tasks._discover_task_modules`` when ``task_app`` loads — no manual
import needed.  Drop a ``.py`` file here with ``@task_app.task(...)`` decorators
and the worker picks it up.
"""
