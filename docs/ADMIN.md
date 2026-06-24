# RBAC Administration Guide

Polyglot uses a role-based access control (RBAC) system built on SQLAlchemy ORM models with FastAPI dependency injection.

## Concepts

| Concept | Description |
|---------|-------------|
| **Permission** | A `(resource, action)` tuple granting one capability (e.g. `"users"`, `"delete"`) |
| **Role** | A named collection of permissions (e.g. `"admin"`, `"auditor"`) |
| **User-Role** | A join table assigning roles to users |
| **is_admin** | Legacy boolean flag on `User` — deprecated in favor of roles but still honored |

## Permission Convention

Permissions follow the format `resource:action`.

Examples:
- `admin:access` — Full administrative dashboard access
- `users:view` — Read user details
- `users:manage` — Create, update, delete users
- `roles:manage` — Create, update, delete roles
- `audit:view` — View audit logs
- `settings:edit` — Modify application settings

## CLI / Management Commands

### Seed Default Roles

The seed script creates two default roles:

```bash
make seed
```

| Role | Permissions |
|------|-------------|
| `admin` | `admin:access`, `users:manage`, `users:view`, `roles:manage`, `audit:view`, `settings:edit` |
| `user` | `users:view` |

### Create a Custom Role via API

```bash
curl -X POST http://localhost:8000/admin/roles \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <csrf>" \
  -b "polyglot_session=<session>" \
  -d '{"name": "editor", "description": "Content editor", "permission_ids": ["<perm-uuid>"]}'
```

### Grant a Role to a User

```bash
curl -X POST http://localhost:8000/admin/users/<user-id>/roles \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <csrf>" \
  -b "polyglot_session=<session>" \
  -d '{"role_id": "<role-uuid>"}'
```

## API Reference

All admin routes require admin access (`is_admin=true` or `admin:access` permission).

### Roles

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/roles` | List all roles |
| `POST` | `/admin/roles` | Create a new role |
| `GET` | `/admin/roles/{role_id}` | Get role by ID |

### Permissions

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/permissions` | List all permissions |
| `POST` | `/admin/permissions` | Create a new permission |

### User Role Assignment

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/users/{user_id}/roles` | Grant role to user |
| `DELETE` | `/admin/users/{user_id}/roles/{role_id}` | Revoke role from user |
| `GET` | `/admin/users/{user_id}/roles` | Get user's roles and permission count |

### Current User

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/me/roles` | Get current user's roles and permissions |

## Using require_permission in Route Handlers

The `require_permission()` factory creates a FastAPI-compatible `Depends()` callable:

```python
from typing import Annotated
from fastapi import Depends
from app.api.deps import require_permission
from app.models.user import User

CanDeleteUsers = Annotated[User, Depends(require_permission("users", "delete"))]

@router.delete("/users/{user_id}")
async def delete_user(user: CanDeleteUsers, db: DbDeps, user_id: UUID):
    ...
```

`is_admin=true` users bypass all permission checks for backward compatibility.

## Database Schema

```
┌──────────┐     ┌───────────────┐     ┌──────────┐
│  users   │────→│  user_roles   │←────│  roles   │
│          │     │  user_id (FK) │     │          │
│  id (PK) │     │  role_id (FK) │     │  id (PK) │
└──────────┘     └───────────────┘     └──────────┘
                                            │
                                            │ role_permissions
                                            │
                                       ┌──────────────┐
                                       │ permissions  │
                                       │  id (PK)     │
                                       │  resource    │
                                       │  action      │
                                       └──────────────┘
```

## Migration

See the SQL comment block at the top of `app/models/role.py` for the `CREATE TABLE` statements.
