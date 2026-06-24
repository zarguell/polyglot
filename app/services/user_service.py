from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import generate_session_token, hash_token
from app.models.auth_session import AuthSession
from app.models.user import User

logger = structlog.get_logger()


async def upsert_user(
    db: AsyncSession,
    *,
    external_subject_id: str,
    email: str,
    display_name: str,
    auth_provider: str,
) -> User:
    """Create or update a user on OIDC login."""
    result = await db.execute(
        select(User).where(User.external_subject_id == external_subject_id),
    )
    user = result.scalar_one_or_none()

    if user:
        user.display_name = display_name
        user.email = email
        user.last_login_at = datetime.now(UTC)
        logger.info("user_updated", user_id=str(user.id), provider=auth_provider)
    else:
        # First user becomes admin
        existing_count = await db.scalar(select(User.id).limit(1))
        is_admin = existing_count is None

        user = User(
            external_subject_id=external_subject_id,
            email=email,
            display_name=display_name,
            auth_provider=auth_provider,
            is_admin=is_admin,
            last_login_at=datetime.now(UTC),
        )
        db.add(user)
        logger.info("user_created", external_subject_id=external_subject_id, is_admin=is_admin)

    await db.flush()
    return user


async def create_session(
    db: AsyncSession,
    user: User,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
    max_age_seconds: int = 43200,
) -> tuple[str, AuthSession]:
    """Create a new auth session. Returns (session_token, session)."""
    token = generate_session_token()
    token_hash = hash_token(token)
    session = AuthSession(
        user_id=user.id,
        session_token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(seconds=max_age_seconds),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(session)
    await db.flush()
    return token, session


async def get_user_by_session(
    db: AsyncSession,
    session_token_hash: str | None,
) -> User | None:
    """Look up a valid, non-expired, non-revoked session and return its user."""
    if not session_token_hash:
        return None
    now = datetime.now(UTC)
    result = await db.execute(
        select(AuthSession)
        .options(selectinload(AuthSession.user))
        .where(
            AuthSession.session_token_hash == session_token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        ),
    )
    session = result.scalar_one_or_none()
    if not session:
        return None
    return session.user


async def revoke_session(db: AsyncSession, user: User, session_token_hash: str) -> None:
    """Mark session as revoked."""
    result = await db.execute(
        select(AuthSession).where(
            AuthSession.session_token_hash == session_token_hash,
            AuthSession.user_id == user.id,
        ),
    )
    session = result.scalar_one_or_none()
    if session:
        session.revoked_at = datetime.now(UTC)
        await db.flush()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
