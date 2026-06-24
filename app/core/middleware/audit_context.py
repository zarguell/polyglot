from __future__ import annotations

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import get_current_actor, set_current_actor
from app.core.security import hash_token
from app.services.user_service import get_user_by_session

logger = structlog.get_logger()


class AuditContextMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts the authenticated user from the session and
    sets the ``current_actor_user_id`` context variable so that downstream
    SQLAlchemy audit hooks can auto-populate ``created_by_user_id`` /
    ``updated_by_user_id``.

    Must be placed **after** ``SessionMiddleware`` in the stack so that
    ``request.session`` is available, and **before** route handlers so
    the context-var is visible during ORM flushes."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        token = request.session.get("session_token")
        if token and not get_current_actor():
            token_hash = hash_token(token)
            try:
                from app.core.db import async_session_factory

                async with async_session_factory() as db:
                    user = await get_user_by_session(db, token_hash)
                    if user:
                        set_current_actor(str(user.id))
            except Exception:
                # Silently skip if DB is unreachable (e.g. SQLite tests
                # without Postgres). The deps.py get_current_user() call
                # will still set the actor on authenticated routes.
                logger.debug("audit_context_skip", reason="db_unreachable")

        response = await call_next(request)
        return response
