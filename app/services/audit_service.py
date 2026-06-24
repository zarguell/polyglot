from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = structlog.get_logger()


async def log_event(
    db: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """Write an audit log entry."""
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_=metadata or {},
        ip_address=ip_address,
        request_id=request_id,
    )
    db.add(entry)
    await db.flush()
    logger.info("audit_log", action=action, actor=actor_user_id)
    return entry


async def log_create(
    db: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    instance: object,
    metadata: dict | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """Log a ``create`` audit event, auto-populating target info from the
    SQLAlchemy model instance."""
    target_type = instance.__class__.__name__
    target_id = _extract_pk(instance)
    return await log_event(
        db,
        actor_user_id=actor_user_id,
        action="create",
        target_type=target_type,
        target_id=target_id,
        metadata=metadata,
        ip_address=ip_address,
        request_id=request_id,
    )


async def log_update(
    db: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    instance: object,
    metadata: dict | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """Log an ``update`` audit event, auto-populating target info from the
    SQLAlchemy model instance."""
    target_type = instance.__class__.__name__
    target_id = _extract_pk(instance)
    return await log_event(
        db,
        actor_user_id=actor_user_id,
        action="update",
        target_type=target_type,
        target_id=target_id,
        metadata=metadata,
        ip_address=ip_address,
        request_id=request_id,
    )


async def log_delete(
    db: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    instance: object,
    metadata: dict | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """Log a ``delete`` audit event, auto-populating target info from the
    SQLAlchemy model instance."""
    target_type = instance.__class__.__name__
    target_id = _extract_pk(instance)
    return await log_event(
        db,
        actor_user_id=actor_user_id,
        action="delete",
        target_type=target_type,
        target_id=target_id,
        metadata=metadata,
        ip_address=ip_address,
        request_id=request_id,
    )


def _extract_pk(instance: object) -> str | None:
    """Best-effort extraction of the primary key value from a model instance."""
    for attr in ("id", "key", "name"):
        val = getattr(instance, attr, None)
        if val is not None:
            return str(val)
    return None


async def get_recent_logs(
    db: AsyncSession,
    *,
    limit: int = 50,
    action: str | None = None,
) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if action:
        query = query.where(AuditLog.action == action)
    result = await db.execute(query)
    return list(result.scalars().all())
