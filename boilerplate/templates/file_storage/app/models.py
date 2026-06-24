"""FileRecord model — metadata for stored files."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class FileRecord(Base):
    __tablename__ = "file_records"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    @property
    def storage_key(self) -> str:
        """The identifier used to address this file in the storage backend.

        Modern records expose ``key``; legacy rows (``key`` is NULL) fall back
        to ``storage_path`` so already-stored files remain retrievable.
        """
        return self.key or self.storage_path
