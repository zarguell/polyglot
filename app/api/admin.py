from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import AdminUser, CurrentUser, DbDeps
from app.schemas.role import (
    GrantRoleRequest,
    PermissionRead,
    RoleCreate,
    RoleRead,
    UserRolesRead,
)
from app.services.rbac_service import (
    count_user_permissions,
    create_permission,
    create_role,
    get_user_roles,
    grant_role,
    list_permissions,
    list_roles,
    revoke_role,
)
from app.services.user_service import get_user_by_id

logger = structlog.get_logger()
router = APIRouter(tags=["admin"], prefix="/admin")


# ── Roles ──────────────────────────────────────────────────────────────────────


@router.get("/roles", response_model=list[RoleRead])
async def admin_list_roles(_admin: AdminUser, db: DbDeps):
    return await list_roles(db)


@router.post("/roles", response_model=RoleRead, status_code=201)
async def admin_create_role(_admin: AdminUser, db: DbDeps, body: RoleCreate):
    role = await create_role(
        db,
        name=body.name,
        description=body.description,
        permission_ids=body.permission_ids,
    )
    if role is None:
        raise HTTPException(status_code=409, detail=f"Role '{body.name}' already exists")
    await db.commit()
    return role


@router.get("/roles/{role_id}", response_model=RoleRead)
async def admin_get_role(_admin: AdminUser, db: DbDeps, role_id: uuid.UUID):
    from app.services.rbac_service import get_role_by_id

    role = await get_role_by_id(db, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


# ── Permissions ────────────────────────────────────────────────────────────────


@router.get("/permissions", response_model=list[PermissionRead])
async def admin_list_permissions(_admin: AdminUser, db: DbDeps):
    return await list_permissions(db)


class CreatePermissionBody(BaseModel):
    resource: str
    action: str
    description: str | None = None


@router.post("/permissions", response_model=PermissionRead, status_code=201)
async def admin_create_permission(_admin: AdminUser, db: DbDeps, body: CreatePermissionBody):
    perm = await create_permission(
        db,
        resource=body.resource,
        action=body.action,
        description=body.description,
    )
    if perm is None:
        raise HTTPException(
            status_code=409,
            detail=f"Permission '{body.resource}:{body.action}' already exists",
        )
    await db.commit()
    return perm


# ── User Role Management ───────────────────────────────────────────────────────


@router.post("/users/{user_id}/roles", status_code=200)
async def admin_grant_role_to_user(
    _admin: AdminUser,
    db: DbDeps,
    user_id: uuid.UUID,
    body: GrantRoleRequest,
):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    result = await grant_role(db, user=user, role_id=body.role_id)
    if not result:
        raise HTTPException(status_code=404, detail="Role not found")
    await db.commit()
    return {"detail": "Role granted"}


@router.delete("/users/{user_id}/roles/{role_id}", status_code=200)
async def admin_revoke_role_from_user(
    _admin: AdminUser,
    db: DbDeps,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    result = await revoke_role(db, user=user, role_id=role_id)
    if not result:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    await db.commit()
    return {"detail": "Role revoked"}


@router.get("/users/{user_id}/roles", response_model=UserRolesRead)
async def admin_get_user_roles(_admin: AdminUser, db: DbDeps, user_id: uuid.UUID):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    roles = await get_user_roles(db, user=user)
    perm_count = await count_user_permissions(db, user=user)

    return UserRolesRead(
        user_id=user.id,
        roles=list(roles),
        permission_count=perm_count,
    )


# ── Current User ───────────────────────────────────────────────────────────────


@router.get("/me/roles", response_model=UserRolesRead)
async def admin_get_my_roles(current_user: CurrentUser, db: DbDeps):
    roles = await get_user_roles(db, user=current_user)
    perm_count = await count_user_permissions(db, user=current_user)

    return UserRolesRead(
        user_id=current_user.id,
        roles=list(roles),
        permission_count=perm_count,
    )
