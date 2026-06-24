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
