from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import set_current_actor
from app.core.db import async_session_factory
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import hash_token
from app.models.user import User
from app.services.rbac_service import has_permission
from app.services.user_service import get_user_by_session


async def get_db() -> AsyncSession:
    """Provide a DB session to route handlers."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


DbDeps = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    request: Request,
    db: DbDeps,
) -> User:
    """Extract the current user from the session cookie."""
    session_token = request.session.get("session_token")
    if not session_token:
        raise UnauthorizedError("Not authenticated")

    token_hash = hash_token(session_token)
    user = await get_user_by_session(db, token_hash)
    if not user:
        raise UnauthorizedError("Session expired or invalid")

    if not user.is_active:
        raise UnauthorizedError("Account deactivated")

    set_current_actor(str(user.id))
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(current_user: CurrentUser) -> User:
    """Ensure the current user has admin role."""
    if not current_user.is_admin:
        raise UnauthorizedError("Admin access required")
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]


def require_permission(resource: str, action: str):
    """Factory: return a Depends callable that checks permission on the current user.

    Usage:
        AdminDeleteUser = Annotated[User, Depends(require_permission("users", "delete"))]
    """

    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.is_admin:
            return current_user

        if not await has_permission(db, user=current_user, resource=resource, action=action):
            raise ForbiddenError(f"Missing permission: {resource}:{action}")

        return current_user

    return _check
