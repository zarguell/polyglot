# SECURITY.md — Polyglot Security Posture

## Defaults

Polyglot ships with secure defaults enabled. No manual hardening is required for basic safety — but read this file before deploying.

## Middleware Chain

1. **Request ID** — X-Request-ID injection for tracing
2. **Structured Logging** — request/response logging with latency
3. **HTTPS Redirect** — automatic redirect when `ENVIRONMENT != local`
4. **Trusted Host** — only hosts in `ALLOWED_HOSTS` are served
5. **Session** — signed cookie via Starlette `SessionMiddleware`
6. **CSRF** — double-submit cookie pattern
7. **Security Headers** — CSP, XFO, HSTS, etc.

## Content Security Policy

Default: `default-src 'self'` with strict exceptions. Script nonces for the CSRF bootstrap.
To add a CDN script, add both the SRI hash and the CSP source.

## Cookie Properties

All auth cookies:
- `HttpOnly` — not accessible to JS
- `Secure` — in non-local environments
- `SameSite=Lax` — prevents CSRF for top-level navigation
- Bounded `Max-Age` — 12 hours default

## CSRF

- Token stored in session
- Every form includes hidden CSRF input
- HTMX global header injection for AJAX
- Exempted endpoints: `/auth/callback` (OIDC redirect), `/webhooks/*` (HMAC)

## HSTS

Enabled when `ENVIRONMENT != local`. `max-age=63072000; includeSubDomains`.

## API Docs

Disabled in non-local environments by default. Override via `ENABLE_OPENAPI=true`.

## Deployment Hardening

1. Set a long random `SECRET_KEY` (min 32 chars).
2. Set `ALLOWED_HOSTS` to the production domain.
3. Set `ENVIRONMENT=production`.
4. Never set `AUTH_DEV_MODE=true` in production.
5. Put behind a reverse proxy (nginx/Caddy) for TLS termination.
6. Configure `forwarded-allow-ips` if behind a proxy.

## Incident Response

1. Rotate `SECRET_KEY` — all sessions will be invalidated.
2. Rotate OIDC client secret.
3. Check audit logs for the affected window.
4. Revoke specific sessions via the `auth_sessions` table.

## Reporting

Report security issues to the maintainer via GitHub Issues.
