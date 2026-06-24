# PRD: Internal Support Ticket System

> Use this PRD to guide an AI agent in building within the Polyglot scaffold.
> After the app is built and running, the agent MUST produce a critical
> retrospective of the **boilerplate itself** (not its own implementation)
> as described in the Deliverables section.

## Problem Statement

The company needs an internal support ticket system where customers can submit
tickets (via email-to-ticket webhook), agents can claim and resolve them, and
admins can monitor SLAs and run reports. The system should support file
attachments, real-time dashboard updates, and email notifications.

## Users / Personas

- **Customer:** Submits tickets via a public-facing form or email webhook.
  No login required for submission, but can check status via a token.
- **Agent:** Claims tickets, adds internal notes, resolves tickets. Sees only
  their assigned tickets + unassigned queue.
- **Admin:** Views all tickets, reassigns, manages agents, configures SLAs,
  runs reports. Can impersonate any queue.

No RBAC beyond these 3 implicit roles (enforced via route logic, not the
`require_permission` factory — this is intentional to test whether the
boilerplate's auth model handles non-standard roles gracefully).

## Core Entities

**Ticket**
- id, uuid PK
- customer_email, customer_name, subject, description (text)
- status: open → assigned → in_progress → resolved → closed
- priority: low, medium, high, critical
- assigned_agent_id (nullable FK to User)
- attachment_paths (JSON list of file_storage keys)
- sla_deadline_at (nullable datetime)
- resolved_at, closed_at
- created_at, updated_at (AuditMixin)

**TicketComment**
- id, ticket_id (FK, cascade), author_id (FK to User)
- body (text), is_internal (bool — agents only, customer doesn't see)
- attachment_paths (JSON list, nullable)
- created_at

**SLA Policy**
- id, priority (low/medium/high/critical), response_time_hours, resolution_time_hours
- created_at, updated_at

**TicketEvent** (audit log for status changes)
- id, ticket_id, actor_id, from_status, to_status, notes, created_at

## Routes

All routes are **JSON API** — the React frontend consumes these.

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/tickets | Customer submits a ticket (public, no auth) |
| GET | /api/tickets | List tickets (agents: assigned+queue, admin: all) |
| GET | /api/tickets/{id} | Ticket detail with comments and events |
| PATCH | /api/tickets/{id} | Update ticket (claim, assign, change status) |
| POST | /api/tickets/{id}/comments | Add comment (internal or public) |
| POST | /api/tickets/{id}/attachments | Upload attachment to ticket |
| GET | /api/tickets/{id}/attachments/{key} | Download attachment |
| GET | /api/queue | Agent's queue (unassigned tickets by priority) |
| GET | /api/tickets/search?q= | Full-text search across tickets |
| GET | /api/admin/reports | Ticket counts by status, priority, agent |
| GET | /api/sse/tickets | SSE endpoint for real-time ticket updates |

## Webhook (Inbound)

- `POST /api/webhooks/email` — receives email-to-ticket payloads from a
  mail forwarding service. Creates a ticket from the email subject/body.
  HMAC-signed. No CSRF. (Activate inbound_webhooks component.)

## Real-Time Updates

- The ticket list and agent queue update in real-time via Server-Sent Events
  (SSE — simpler than WebSockets for this use case, but tests the same
  connection-upgrade path). When a ticket is created, claimed, or updated,
  an event is pushed to connected clients.
- If SSE doesn't compose well with the component system, fall back to
  polling every 15 seconds (document the reason in the retrospective).

## Pages (React + Vite — the `frontend/` directory)

Build a single-page React app that consumes the JSON API. Use the existing
frontend scaffolding in `frontend/` — don't create a new React project.

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | TicketList | Filterable list of tickets, auto-refreshes via SSE |
| `/tickets/new` | TicketForm | Public submission form |
| `/tickets/{id}` | TicketDetail | Detail view with comments, attachments, status actions |
| `/queue` | AgentQueue | Unassigned tickets sorted by priority, claim button |
| `/admin` | AdminDashboard | Reports, SLA config, agent management |

**Styling**: Use the existing Tailwind config in `frontend/`. Refer to
`DESIGN_TOKENS.json` for colors and spacing. Don't add a UI library.

## File Attachments

- Activate the `file_storage` component.
- Attachments are uploaded to a ticket via `POST /api/tickets/{id}/attachments`.
- Stored via `file_storage`, referenced by key in `ticket.attachment_paths`.
- Max 10MB per file.
- Listed inline in the ticket detail view.

## Notifications

- **Email** (via SMTP component):
  - To customer when ticket is created (auto-reply with ticket ID)
  - To agent when assigned a ticket
  - To customer when ticket is resolved
- **SSE push** (real-time):
  - New ticket in queue → agent dashboard updates
  - Ticket status change → detail view updates

## Background Tasks (Procrastinate)

| Task | Schedule | Description |
|------|----------|-------------|
| `tickets.escalate_overdue` | Every 15 min | Check tickets past SLA deadline, escalate priority |
| `tickets.close_stale_resolved` | Daily 3 AM | Auto-close tickets resolved > 7 days |

## SLA Enforcement

Each priority level has a response time and resolution time. When a ticket
is created or escalated, `sla_deadline_at` is computed. The escalation cron
checks `WHERE status NOT IN ('resolved','closed') AND sla_deadline_at < now()`.
If found, bumps priority by one level and logs a `TicketEvent`.

## Optional Components to Activate

```
make activate-component COMPONENT=smtp
make activate-component COMPONENT=file_storage
make activate-component COMPONENT=inbound_webhooks
make activate-component COMPONENT=outbound_webhooks
make activate-component COMPONENT=reporting_exports
```

## Non-Functional Requirements

- Ticket list must load under 2s for 1000 tickets
- File uploads limited to 10MB per file
- SSE connections must not block the worker
- Customers must not see internal comments (is_internal=true)
- Ticket status transitions must be validated server-side
- Every status change recorded in TicketEvent (immutable audit log)
- All API routes (except ticket creation) require auth
- Inbound webhook endpoint uses HMAC, not CSRF

## Deliverables

The built app must:

1. Run on `localhost:8000` with `make up` (React frontend included)
2. Pass `make lint` and `make test`
3. Pass `make smoke-test` (server running, pages render)

**After the app is verified running**, produce a critical retrospective
of the **Polyglot boilerplate itself** (not your implementation). Evaluate:

- **React path**: Did the frontend scaffolding work? Build pipeline?
  API client setup? Any impedance mismatch between the Jinja and
  React templates (DESIGN_TOKENS.json consumed by both)?
- **Component composition**: Activate 5 components. Did they compose
  cleanly? Any import order issues, route collisions, dependency
  conflicts? Did SSE/WebSocket upgrade work through the middleware
  stack (BodyCache, CSRF, Session)?
- **File storage**: Upload, download, reference by key. Did it work
  first time or were there configuration gaps?
- **Inbound webhooks**: HMAC verification, CSRF exemption, payload
  parsing. Did the component doc match reality?
- **SSE / real-time**: Did SSE work through Starlette's
  BaseHTTPMiddleware without issues? (This is a known pain point.)
- **What broke**: Be specific. File paths. Line numbers. Stack traces.
- **What surprised you** (good or bad): Something that worked
  unexpectedly well, or something that failed in a way you didn't
  anticipate.
- **The 10-minute test**: What's the first thing a new developer
  would get wrong with this boilerplate today?

Write the retrospective to `BOILERPLATE_RETRO.md` in the project root.
Be adversarial. This is a pressure test, not a thank-you note.
