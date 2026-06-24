from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory
from app.core.errors import UnauthorizedError
from app.core.security import hash_token
from app.models.user import User
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

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(current_user: CurrentUser) -> User:
    """Ensure the current user has admin role."""
    if not current_user.is_admin:
        raise UnauthorizedError("Admin access required")
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
