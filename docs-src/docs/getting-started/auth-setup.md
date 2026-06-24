# Authentication Setup

Polyglot supports three authentication modes. Choose one:

## 1. Dev Login (Local Only)

For development without an identity provider:

```bash
AUTH_DEV_MODE=true
ENVIRONMENT=local
```

Visit `/login` — a simple form creates a session for any email. The first user becomes admin.

!!! danger "Never enable AUTH_DEV_MODE in production"
    The app asserts `ENVIRONMENT != production` when dev mode is on and refuses to boot.

## 2. OIDC SSO

Polyglot ships with 4 OIDC provider presets:

| Provider | `AUTH_OIDC_PROVIDER` | Required Env |
|----------|---------------------|--------------|
| Generic | `generic` | `AUTH_OIDC_DISCOVERY_URL` |
| Microsoft Entra ID | `entra` | `AUTH_OIDC_TENANT` |
| Okta | `okta` | `AUTH_OIDC_DOMAIN` |
| Google Workspace | `google` | — (uses Google's discovery URL) |

All providers require:
```bash
AUTH_OIDC_CLIENT_ID=your-client-id
AUTH_OIDC_CLIENT_SECRET=your-client-secret
```

The login flow:

1. User clicks Sign In → redirected to IdP
2. IdP authenticates → redirects to `/auth/callback`
3. App exchanges code for tokens, upserts user, creates session
4. User lands on dashboard

## 3. SAML SSO

Enable SAML when you need to integrate with a SAML 2.0 identity provider:

```bash
AUTH_SAML_ENABLED=true
AUTH_SAML_IDP_METADATA_URL=https://your-idp.com/metadata
AUTH_SAML_SP_ENTITY_ID=polyglot
AUTH_SAML_SP_PRIVATE_KEY=...  # PEM-encoded
AUTH_SAML_SP_CERT=...         # PEM-encoded
```

The SAML SP metadata endpoint is at `/auth/saml/metadata` — register this with your IdP.

## Auto-Provisioning

The first user to authenticate (via any method) is automatically granted `is_admin=true`. Subsequent users get `is_admin=false` by default.
