# DECISIONS.md — Architecture Decision Records

## ADR-001: FastAPI First

**Context:** We needed a Python web framework that supports async, has strong middleware primitives, and is easy for AI agents to reason about.

**Decision:** Start with FastAPI. It has built-in HTTPS redirect and trusted host middleware, Pydantic integration, and a simple routing model.

**When to revisit:** When the app needs Django's admin framework, complex permission system (>2 roles), or metadata-heavy entity management.

## ADR-002: Postgres Everywhere

**Context:** Minimize infrastructure surface. Avoid running Redis, RabbitMQ, or other backing services until they prove necessary.

**Decision:** Use Postgres for application data, session tracking, task queue (via Procrastinate), audit logs, and app settings.

**Trade-off:** Task throughput is lower than Redis-based queues. Mitigation: tasks should be short-lived; long-running jobs should be rare.

## ADR-003: Procrastinate over Redis Queues

**Context:** Need a task queue that doesn't force Redis into the initial setup.

**Decision:** Use Procrastinate — a Postgres-native task queue with async support, periodic scheduling, and retry.

**Rationale:** Keeps the initial deploy to Postgres only. Redis is a later optimization if queue volume demands it.

## ADR-004: SQLAlchemy 2.0 Async

**Context:** ORM choice for the FastAPI stack.

**Decision:** SQLAlchemy 2.0 with async sessions and asyncpg driver.

**Rationale:** More ecosystem support than SQLModel, more flexible for complex queries, mature async support.

## ADR-005: Copy-on-Activate Components

**Context:** Need a way to ship optional capabilities without bloating the active codebase.

**Decision:** Templates live in `boilerplate/templates/`. Activation = copy files into `app/components/`. Each component self-registers via a `register()` function.

**Rationale:** User owns the code after activation. No "magic" import. AI agents can see exactly what code is active. Clean separation of concerns.

## ADR-006: Tailwind v4 Standalone (not Play CDN)

**Context:** Need a CSS framework that's fast to build, looks good, and works with strict CSP.

**Decision:** Tailwind v4 compiled via standalone CLI binary. Self-hosted output.

**Rationale:** Play CDN injects runtime `<style>` blocks that violate strict CSP. Compiled output is static, hashable, and same-origin.

## ADR-007: Server-Side Sessions with Revocation

**Context:** Need ability to invalidate sessions server-side.

**Decision:** Starlette SessionMiddleware for transport (signed cookie), `auth_sessions` table for server-side tracking.

**Rationale:** Cookie-only sessions can't be individually revoked. Server-side sessions allow forced logout, suspension, and audit.

## ADR-008: Postgres Row-Level Security

**Context:** Multi-tenant applications need hard tenant isolation to prevent cross-tenant data leakage at every layer. Application-level checks are necessary but can be bypassed by bugs or misconfigurations.

**Decision:** Use Postgres Row-Level Security (RLS) as a defense-in-depth layer for multi-tenant tables. Application-layer checks (service-layer tenant scoping) remain the primary enforcement mechanism.

**When to use RLS:**
- Multi-tenant apps with hard tenant boundaries (e.g., separate organizations with zero data sharing)
- Tables where a single accidental query omission would expose another tenant's data
- Compliance-heavy domains (HIPAA, SOC 2) where database-level guarantees reduce audit scope

**When NOT to use RLS:**
- Single-tenant applications
- Soft multi-tenancy (e.g., projects within a single org)
- Tables where tenant isolation is already guaranteed by the data model (e.g., user-scoped data keyed by user_id)

**Implementation pattern:**

```sql
-- Enable RLS on a table
ALTER TABLE my_table ENABLE ROW LEVEL SECURITY;

-- Create a tenant isolation policy
CREATE POLICY tenant_isolation ON my_table
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- Set the session variable per request
SET app.tenant_id = '550e8400-e29b-41d4-a716-446655440000';
```

In the application layer, set the tenant via a SQLAlchemy connection event:

```python
from sqlalchemy import event
from app.core.context import get_current_actor

@event.listens_for(engine.sync_engine, "connect")
def set_tenant(dbapi_connection, connection_record):
    # Only for Postgres; SQLite (tests) ignores this
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("SELECT set_config('app.tenant_id', %s, false)", (tenant_id,))
    except Exception:
        pass  # Skip for SQLite / non-Postgres environments
```

**Limitations:**
- **Not testable with SQLite**: RLS is Postgres-only. Integration tests must be marked `@pytest.mark.integration`.
- **Migrations must be explicit**: Each policy needs its own Alembic migration as `op.execute()` statements.
- **Performance**: RLS policies add a WHERE clause to every query on that table. Keep policies simple and index the filtering column.
- **Requires the `postgres` superuser or `ALTER TABLE` grant to enable RLS and create policies.
- **pg_dump/restore**: Policies are included in schema dumps but require the same Postgres version for restore.

**RLS policy migration example:**

```python
# alembic/versions/xxxx_add_rls_policies.py
def upgrade():
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON users
        USING (tenant_id = current_setting('app.tenant_id')::uuid)
    """)

def downgrade():
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
```

**Recommendation:** Use application-level checks (service-layer tenant scoping) before RLS. RLS is defense-in-depth — it should never be the only isolation mechanism, and it should not be deployed until the application-level checks are in place and tested.
