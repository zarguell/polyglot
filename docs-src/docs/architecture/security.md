# Security Model

## Middleware Chain (Inbound Order)

1. **RequestIdMiddleware** — injects `X-Request-ID`, sets structlog context
2. **StructuredLoggingMiddleware** — logs method, path, status, latency
3. **NonceMiddleware** — per-request CSP nonce
4. **CSRFMiddleware** — double-submit cookie pattern
5. **SessionMiddleware** — signed Starlette session cookie
6. **SecurityHeadersMiddleware** — CSP, HSTS, XFO, etc.

## Content Security Policy

```
default-src 'self'
style-src 'self'
script-src 'self' 'nonce-{random}'
frame-ancestors 'none'
base-uri 'self'
```

The only inline script is the CSRF bootstrap — protected by a per-request nonce.

## CSRF Protection

- Token stored in server session
- Every form includes hidden `csrf_token` input
- HTMX requests use auto-injected `X-CSRFToken` header
- Exemptions: `/auth/callback` (OIDC redirect), `/auth/saml/acs` (IdP POST), `/webhooks/*` (HMAC)

## Session Security

- **HttpOnly** — not accessible to JavaScript
- **Secure** — in non-local environments
- **SameSite=Lax** — CSRF protection for top-level navigations
- **12-hour max age** — configurable via `SESSION_MAX_AGE_SECONDS`
- **Server-side revocation** — sessions can be invalidated individually

## Audit Logging

Every auth-relevant event is logged to both:

- **Structured logs** (JSON in production, console in local)
- **`audit_logs` table** in Postgres with actor, action, target, IP, request ID

Events tracked: login, logout, failed login, settings change, component activation.

## Role-Based Access Control

```python
# Usage in routes
from app.api.deps import require_permission

DeleteUsers = Annotated[User, Depends(require_permission("users", "delete"))]

@router.delete("/users/{id}")
async def delete_user(user: DeleteUsers, id: UUID):
    ...
```

Built-in roles: `admin` (full access), `user` (base role). Roles and permissions are stored in Postgres tables with many-to-many relationships.

## Row-Level Security (RLS)

For multi-tenant deployments, Postgres RLS is documented as an additional defense layer:

- Service-layer tenant scoping is the primary mechanism
- RLS is defense-in-depth, not a replacement
- Policies are implemented via Alembic migrations with `op.execute()`
- Session variable `app.tenant_id` is set on each authenticated request
