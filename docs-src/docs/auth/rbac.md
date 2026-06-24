# RBAC — Role-Based Access Control

## Models

```
Role (id, name, description, is_system, created_at)
Permission (id, resource, action, description, created_at)
UserRole (user_id, role_id)          # join table
RolePermission (role_id, permission_id)  # join table
```

## Service Functions

```python
from app.services.rbac_service import (
    grant_role, revoke_role,
    has_permission, get_user_permissions,
    create_role, create_permission,
)
```

## Dependency

```python
from app.api.deps import require_permission

# Create a dependency that checks a specific permission
AdminDeleteUsers = Annotated[User, Depends(require_permission("users", "delete"))]

@router.delete("/users/{id}")
async def delete_user(user: AdminDeleteUsers, id: UUID):
    ...
```

The `require_permission` factory returns a FastAPI dependency that:

1. Resolves the current user
2. Checks `is_admin` — admins bypass all permission checks
3. Queries the RBAC join tables for the specific permission
4. Returns 403 if the user lacks the permission

## Admin Routes

When the RBAC system is active, admin CRUD routes are available under `/api/admin/`:

- `GET /api/admin/roles` — list roles with permissions
- `POST /api/admin/roles` — create role
- `POST /api/admin/roles/{id}/permissions` — assign permissions
- `GET /api/admin/permissions` — list permissions
- `POST /api/admin/permissions` — create permission
- `POST /api/admin/users/{id}/roles` — grant role to user
- `DELETE /api/admin/users/{id}/roles/{role_id}` — revoke role
