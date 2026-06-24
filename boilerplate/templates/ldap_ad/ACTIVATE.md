# LDAP/AD Component — Activation Guide

## What This Component Adds

- `POST /api/ldap/sync` — trigger a full LDAP user synchronization
- `GET /api/ldap/status` — check LDAP configuration status
- `LDAPService` — wraps the `ldap3` library for user search and sync
- `sync_ldap_users` Procrastinate task — periodic background sync of LDAP users into local User table

## Prerequisites

Install additional dependencies:

```bash
uv add ldap3
```

## Environment Variables

Add to your `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `LDAP_SERVER` | Yes | — | LDAP/AD server hostname (e.g., `ldap://ad.example.com`) |
| `LDAP_PORT` | No | `389` | LDAP port |
| `LDAP_USE_TLS` | No | `true` | Use TLS/SSL connection |
| `LDAP_BIND_DN` | Yes | — | Bind DN (e.g., `cn=admin,dc=example,dc=com`) |
| `LDAP_BIND_PASSWORD` | Yes | — | Bind password |
| `LDAP_BASE_DN` | Yes | — | Base DN for user search |
| `LDAP_USER_FILTER` | No | `(objectClass=person)` | LDAP filter for user search |

### Example

```bash
LDAP_SERVER=ldap://ad.corp.example.com
LDAP_PORT=389
LDAP_USE_TLS=true
LDAP_BIND_DN=cn=service-account,dc=corp,dc=example,dc=com
LDAP_BIND_PASSWORD=your_password_here
LDAP_BASE_DN=dc=corp,dc=example,dc=com
LDAP_USER_FILTER=(objectClass=person)
```

## Infrastructure

The LDAP/AD server is external infrastructure — no additional Docker services are required. Ensure network connectivity from the app container to the LDAP server.

## Migration

No additional database tables are needed. The component syncs users into the existing `users` table.

## Verification

```bash
# Run tests
pytest tests/unit/test_ldap_ad.py -v
```

## Scheduling Periodic Sync

To run LDAP sync on a schedule, set up a cron trigger or Procrastinate periodic task:

```bash
# Trigger sync via API
curl -X POST http://localhost:8000/api/ldap/sync \
  -H "Authorization: Bearer <token>"
```

## File Layout After Activation

```
app/components/ldap_ad/
├── __init__.py          # register() — wires router and tasks
├── api.py               # POST /api/ldap/sync, GET /api/ldap/status
├── service.py           # LDAPService wrapping ldap3
└── tasks.py             # sync_ldap_users periodic task
```
