"""TOTP Multi-Factor Authentication component.

Provides time-based one-time password (TOTP) MFA using RFC 6238,
with backup codes for account recovery.

Activation:
    This component is auto-discovered by the app factory when
    ``totp_mfa`` appears in ``INSTALLED_COMPONENTS``. The factory
    calls ``register(app=..., settings=...)`` below.

Registration does three things:
    1. Includes the MFA page router (``/mfa/*`` routes).
    2. Adds the ``MFAMiddleware`` that intercepts ``/app`` requests
       and redirects users with active MFA devices to the challenge
       page until they verify.
    3. Registers the ``MFADevice`` model — it will be picked up in
       the next Alembic autogenerate migration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.core.config import Settings

logger = structlog.get_logger()


def register(app: FastAPI, settings: Settings) -> None:
    """Register MFA routes and middleware with the FastAPI app.

    Called by the app factory during startup (see ``app/main.py``).
    """
    from app.components.totp_mfa.api import router
    from app.components.totp_mfa.middleware import MFAMiddleware

    # Include MFA routes at root level so they are accessible at
    # /mfa/setup, /mfa/challenge, etc. (not /api/mfa/...).
    app.include_router(router, prefix="")

    # Add middleware that intercepts /app requests and redirects
    # users with active MFA devices to the challenge page.
    # Added first (innermost) so it runs after SessionMiddleware
    # populates request.session but before the route handler.
    app.add_middleware(MFAMiddleware)

    logger.info("totp_mfa_registered")
