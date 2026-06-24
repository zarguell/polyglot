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
