from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid_pk

if TYPE_CHECKING:
    from app.models.user import User

# ── Migration SQL ──────────────────────────────────────────────────────────────
# Run these via alembic or manually for Postgres:
#
# CREATE TABLE permissions (
#     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#     resource VARCHAR(64) NOT NULL,
#     action VARCHAR(64) NOT NULL,
#     description TEXT,
#     created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
#     CONSTRAINT uq_permissions_resource_action UNIQUE (resource, action)
# );
#
# CREATE TABLE roles (
#     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
#     name VARCHAR(128) NOT NULL,
#     description TEXT,
#     is_system BOOLEAN NOT NULL DEFAULT FALSE,
#     created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
#     CONSTRAINT uq_roles_name UNIQUE (name)
# );
#
# CREATE TABLE role_permissions (
#     role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
#     permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
#     PRIMARY KEY (role_id, permission_id)
# );
#
# CREATE TABLE user_roles (
#     user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
#     role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
#     PRIMARY KEY (user_id, role_id)
# );
# ────────────────────────────────────────────────────────────────────────────────

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Many-to-many: Role <-> Permission
    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary=role_permissions,
        lazy="selectin",
        back_populates="roles",
    )

    # Many-to-many backref: Role <-> User via user_roles
    users: Mapped[list[User]] = relationship(
        "User",
        secondary="user_roles",
        lazy="selectin",
        back_populates="roles",
    )

    __table_args__ = (UniqueConstraint("name", name="uq_roles_name"),)


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = uuid_pk()
    resource: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Many-to-many: Permission <-> Role
    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary=role_permissions,
        lazy="selectin",
        back_populates="permissions",
    )

    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),
    )
