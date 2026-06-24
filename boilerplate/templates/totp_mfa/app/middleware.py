from __future__ import annotations

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

logger = structlog.get_logger()

# Paths that require MFA verification before access
MFA_PROTECTED_PATHS: tuple[str, ...] = ("/app",)

# Paths that are part of the MFA flow itself (no redirect loop)
MFA_FLOW_PATHS: tuple[str, ...] = (
    "/mfa/challenge",
    "/mfa/setup",
    "/mfa/verify",
    "/mfa/backup-codes",
)

# Public paths that never need MFA checks
MFA_EXEMPT_PATHS: tuple[str, ...] = (
    "/login",
    "/login/dev",
    "/logout",
    "/auth/callback",
    "/healthz",
    "/readyz",
    "/",
    "/static",
    "/docs",
    "/redoc",
    "/me",
)


class MFAMiddleware(BaseHTTPMiddleware):
    """Middleware that redirects authenticated users with active MFA
    devices to the challenge page before allowing access to protected paths.

    Flow:
    1. User logs in → session_token set → redirect to /app
    2. This middleware intercepts /app:
       a. Check if user is authenticated (has session_token)
       b. Check if user has an active MFA device in DB
       c. If yes and session lacks mfa_verified → redirect to /mfa/challenge
    3. User completes MFA challenge → mfa_verified set in session → redirect to /app
    4. This middleware now lets them through
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip middleware for exempt paths
        if any(path.startswith(p) for p in MFA_EXEMPT_PATHS):
            return await call_next(request)

        # Skip middleware for MFA flow pages (prevent redirect loop)
        if any(path.startswith(p) for p in MFA_FLOW_PATHS):
            return await call_next(request)

        # Only apply to protected paths
        if not any(path.startswith(p) for p in MFA_PROTECTED_PATHS):
            return await call_next(request)

        # Check if user is authenticated
        session_token = request.session.get("session_token")
        if not session_token:
            return await call_next(request)

        # If MFA is already verified in this session, allow through
        if request.session.get("mfa_verified"):
            return await call_next(request)

        # Check if user has an active MFA device
        has_mfa = await _user_has_active_mfa(request, session_token)
        if not has_mfa:
            return await call_next(request)

        # User needs MFA — redirect to challenge
        logger.info(
            "mfa_challenge_required",
            path=path,
        )
        request.session["mfa_return_to"] = path
        return RedirectResponse(url="/mfa/challenge", status_code=302)


async def _user_has_active_mfa(request: Request, session_token: str) -> bool:
    """Check whether the current user has an active MFA device."""
    from app.api.deps import get_current_user

    try:
        from app.core.db import async_session_factory

        async with async_session_factory() as db:
            user = await get_current_user(request, db)
            if not user:
                return False

            from sqlalchemy import select

            from app.components.totp_mfa.models import MFADevice

            result = await db.execute(
                select(MFADevice).where(
                    MFADevice.user_id == user.id,
                    MFADevice.is_active.is_(True),
                ),
            )
            device = result.scalar_one_or_none()
            return device is not None
    except Exception:
        logger.exception("mfa_check_failed")
        return False
