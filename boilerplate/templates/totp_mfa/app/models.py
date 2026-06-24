from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class MFADevice(Base):
    """Represents a TOTP multi-factor authentication device bound to a user.

    Each user may have at most one active device. The secret is stored
    in plaintext because TOTP is a shared-secret protocol — the server
    must know the secret to verify codes. Protect the database
    accordingly (encryption at rest, access controls).
    """

    __tablename__ = "mfa_devices"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    secret: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    backup_code_hashes: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationship to User — note: this requires the User model to have
    # mfa_devices = relationship("MFADevice", ...) defined later.
    # Since we can't modify the core User model, we use a manual join
    # in service queries instead of an ORM relationship.
