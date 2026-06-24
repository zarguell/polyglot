# Configuration

Polyglot uses `pydantic-settings` to read configuration from environment variables or `.env` file.

## Core Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_NAME` | str | `Polyglot` | Application display name |
| `ENVIRONMENT` | enum | `local` | `local`, `dev`, `staging`, `production` |
| `SECRET_KEY` | SecretStr | — | **Required.** Min 32 chars in production |
| `ENABLE_OPENAPI` | bool | `True` local only | Enable `/docs` and `/redoc` |
| `DATABASE_URL` | PostgresDsn | — | Async Postgres connection string |

## Auth Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTH_DEV_MODE` | bool | `False` | Dev login bypass (local only) |
| `AUTH_OIDC_PROVIDER` | enum | `generic` | `generic`, `entra`, `okta`, `google` |
| `AUTH_OIDC_CLIENT_ID` | str | — | OIDC client ID |
| `AUTH_OIDC_CLIENT_SECRET` | SecretStr | — | OIDC client secret |
| `AUTH_DEV_MODE` | bool | `False` | Dev login bypass (local only) |
| `AUTH_SAML_ENABLED` | bool | `False` | Enable SAML SSO |
| `AUTH_SAML_IDP_METADATA_URL` | str | — | IdP metadata URL |
| `SESSION_MAX_AGE_SECONDS` | int | `43200` | 12 hours |

## Security Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ALLOWED_HOSTS` | list | `localhost,127.0.0.1` | Trusted host validation |
| `CORS_ALLOWED_ORIGINS` | list | — | CORS origins (SPA mode) |

## Component Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `INSTALLED_COMPONENTS` | list | — | Explicit allowlist (comma-separated) |

## Startup Safety Checks

The app refuses to boot if:

- `ENVIRONMENT=production` and `AUTH_DEV_MODE=true` — dev mode forbidden in prod
- `ENVIRONMENT != local` and `SECRET_KEY < 32 chars` — weak secret
- `ENVIRONMENT != local` — automatically disables OpenAPI docs in non-local
