from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resource: str
    action: str
    description: str | None = None
    created_at: datetime


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    permission_ids: list[uuid.UUID] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    permission_ids: list[uuid.UUID] | None = None


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    is_system: bool
    created_at: datetime
    permissions: list[PermissionRead] = Field(default_factory=list)


class UserRolesRead(BaseModel):
    user_id: uuid.UUID
    roles: list[RoleRead] = Field(default_factory=list)
    permission_count: int = 0


class GrantRoleRequest(BaseModel):
    role_id: uuid.UUID


class RevokeRoleRequest(BaseModel):
    role_id: uuid.UUID
