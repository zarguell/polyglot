from __future__ import annotations

import uuid

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.role import Permission, Role
from app.models.user import User
from app.models.user_role import UserRole

logger = structlog.get_logger()


async def grant_role(
    db: AsyncSession,
    *,
    user: User,
    role_id: uuid.UUID,
) -> bool:
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        return False

    exists = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role_id,
        ),
    )
    if exists.scalar_one_or_none() is not None:
        return True

    db.add(UserRole(user_id=user.id, role_id=role_id))
    await db.flush()
    logger.info("role_granted", user_id=str(user.id), role_id=str(role_id), role_name=role.name)
    return True


async def revoke_role(
    db: AsyncSession,
    *,
    user: User,
    role_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role_id,
        ),
    )
    link = result.scalar_one_or_none()
    if link is None:
        return False

    await db.delete(link)
    await db.flush()
    logger.info("role_revoked", user_id=str(user.id), role_id=str(role_id))
    return True


async def has_permission(
    db: AsyncSession,
    *,
    user: User,
    resource: str,
    action: str,
) -> bool:
    result = await db.execute(
        select(func.count(Permission.id))
        .join(Permission.roles)
        .join(Role.users)
        .where(
            User.id == user.id,
            Permission.resource == resource,
            Permission.action == action,
        ),
    )
    count = result.scalar() or 0
    return count > 0


async def get_user_permissions(
    db: AsyncSession,
    *,
    user: User,
) -> list[Permission]:
    result = await db.execute(
        select(Permission)
        .join(Permission.roles)
        .join(Role.users)
        .where(User.id == user.id)
        .order_by(Permission.resource, Permission.action),
    )
    return list(result.scalars().all())


async def get_user_roles(
    db: AsyncSession,
    *,
    user: User,
) -> list[Role]:
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions))
        .join(Role.users)
        .where(User.id == user.id)
        .order_by(Role.name),
    )
    return list(result.scalars().all())


async def get_permissions_for_role(
    db: AsyncSession,
    *,
    role: Role,
) -> list[Permission]:
    result = await db.execute(
        select(Permission)
        .join(Permission.roles)
        .where(Role.id == role.id)
        .order_by(Permission.resource, Permission.action),
    )
    return list(result.scalars().all())


async def count_user_permissions(
    db: AsyncSession,
    *,
    user: User,
) -> int:
    result = await db.execute(
        select(func.count(func.distinct(Permission.id)))
        .join(Permission.roles)
        .join(Role.users)
        .where(User.id == user.id),
    )
    return result.scalar() or 0


async def create_role(
    db: AsyncSession,
    *,
    name: str,
    description: str | None = None,
    permission_ids: list[uuid.UUID] | None = None,
    is_system: bool = False,
) -> Role | None:
    existing = await db.scalar(
        select(Role).options(selectinload(Role.permissions)).where(Role.name == name),
    )
    if existing is not None:
        return None

    role = Role(name=name, description=description, is_system=is_system)
    db.add(role)
    await db.flush()

    if permission_ids:
        perms_result = await db.execute(
            select(Permission).where(Permission.id.in_(permission_ids)),
        )
        role.permissions = list(perms_result.scalars().all())

    await db.flush()
    logger.info("role_created", role_id=str(role.id), name=name)
    return role


async def create_permission(
    db: AsyncSession,
    *,
    resource: str,
    action: str,
    description: str | None = None,
) -> Permission | None:
    existing = await db.scalar(
        select(Permission).where(
            Permission.resource == resource,
            Permission.action == action,
        ),
    )
    if existing is not None:
        return None

    permission = Permission(resource=resource, action=action, description=description)
    db.add(permission)
    await db.flush()
    logger.info("permission_created", resource=resource, action=action)
    return permission


async def list_roles(db: AsyncSession) -> list[Role]:
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).order_by(Role.name),
    )
    return list(result.scalars().all())


async def list_permissions(db: AsyncSession) -> list[Permission]:
    result = await db.execute(
        select(Permission).order_by(Permission.resource, Permission.action),
    )
    return list(result.scalars().all())


async def get_role_by_id(db: AsyncSession, role_id: uuid.UUID) -> Role | None:
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id),
    )
    return result.scalar_one_or_none()


async def get_permission_by_id(db: AsyncSession, permission_id: uuid.UUID) -> Permission | None:
    result = await db.execute(
        select(Permission).where(Permission.id == permission_id),
    )
    return result.scalar_one_or_none()
