from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, MetaData, Uuid, event, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    metadata = metadata


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )


def utcnow() -> datetime:
    return datetime.now(UTC)


class AuditMixin:
    """Mixin providing audit columns and SQLAlchemy event hooks.

    Adds ``created_at``, ``updated_at``, ``created_by_user_id``, and
    ``updated_by_user_id`` to any model that inherits it.  The FK columns
    are nullable and use ON DELETE SET NULL so the audit trail survives
    user deletion.

    Event listeners wired at module import time automatically populate the
    actor columns from ``app.core.context.get_current_actor()`` on insert
    and update.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


# ── Event listeners for AuditMixin ────────────────────────────────


def _audit_set_actor(
    _mapper: object,
    _connection: object,
    target: object,
) -> None:
    """Populate ``created_by_user_id`` / ``updated_by_user_id`` from context-var."""
    from app.core.context import get_current_actor  # noqa: PLC0415

    actor_str = get_current_actor()
    if not actor_str:
        return

    try:
        actor_id = uuid.UUID(actor_str)
    except (ValueError, TypeError):
        return

    # Use hasattr guards so models that extend Base directly (without AuditMixin)
    # don't crash on insert/update.
    if hasattr(target, "created_by_user_id") and not target.created_by_user_id:
        target.created_by_user_id = actor_id
    if hasattr(target, "updated_by_user_id"):
        target.updated_by_user_id = actor_id


event.listen(Base, "before_insert", _audit_set_actor, propagate=True)
event.listen(Base, "before_update", _audit_set_actor, propagate=True)
