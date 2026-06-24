# TOTP Multi-Factor Authentication Component

Adds time-based one-time password (TOTP / RFC 6238) multi-factor
authentication to the Polyglot application. Users scan a QR code with
an authenticator app (Google Authenticator, Authy, 1Password, etc.)
and must enter a 6-digit code on login.

Also provides single-use backup codes for account recovery when the
authenticator app is unavailable.

## Prerequisites

Install the required Python packages:

```bash
uv add pyotp qrcode
# or
pip install pyotp qrcode[pil]
```

## Activation

```bash
make activate-component COMPONENT=totp_mfa
```

This copies the component into `app/components/totp_mfa/` and adds
`totp_mfa` to `INSTALLED_COMPONENTS` in `.env`.

## Environment Variables

Add the following to your `.env` file:

```
TOTP_ISSUER=Polyglot
```

The `TOTP_ISSUER` sets the label shown in the user's authenticator app
(e.g., "Polyglot: user@example.com"). Change it to your app's name.

## Database Migration

After activation, generate and apply a migration for the new
`mfa_devices` table:

```bash
alembic revision --autogenerate -m "add mfa_devices"
alembic upgrade head
```

## Test the Component

Copy the test file to your test suite:

```bash
cp boilerplate/templates/totp_mfa/tests/test_totp.py tests/unit/
uv run pytest tests/unit/test_totp.py -v
```

## How It Works

### Registration
On startup, `app/main.py` discovers the component and calls
`register(app, settings)`, which:

1. Registers MFA routes at `/mfa/setup`, `/mfa/challenge`,
   `/mfa/disable`, `/mfa/backup-codes`
2. Adds `MFAMiddleware` that intercepts `/app` requests

### Login Flow with MFA Enabled

1. User logs in normally (dev login or OIDC)
2. Session cookie is set, user is redirected to `/app`
3. `MFAMiddleware` intercepts `/app`:
   - Checks if user has an active `mfa_devices` record
   - If yes and `mfa_verified` not in session: redirect to `/mfa/challenge`
   - If no MFA device: allow access to `/app`
4. User enters TOTP code (or backup code) on challenge page
5. If valid: `mfa_verified` set in session, redirected to `/app`
6. If invalid: error shown, user can retry

### Enabling MFA

1. Navigate to `/mfa/setup`
2. Scan the QR code with an authenticator app
3. Save the backup codes shown on screen
4. Enter the 6-digit verification code from the app
5. MFA is now active

### Disabling MFA

Navigate to `/mfa/disable`, type "disable" to confirm.

### Backup Codes

Navigate to `/mfa/backup-codes` to regenerate. Old codes are
invalidated. Each code is single-use.

## Files

```
app/components/totp_mfa/
├── __init__.py          # register() called by app factory
├── api.py               # Page routes (GET/POST /mfa/*)
├── middleware.py         # MFAMiddleware for /app interception
├── models.py            # MFADevice SQLAlchemy model
├── schemas.py           # Pydantic request/response schemas
├── service.py           # TOTP logic (pyotp, backup codes)
├── template_loader.py    # Jinja2 env with component templates
└── templates/
    ├── mfa_setup.html      # QR code + verification form
    ├── mfa_challenge.html  # Post-login challenge form
    ├── mfa_disable.html    # Disable confirmation
    └── mfa_backup_codes.html # Regenerated codes display
```

## Security Notes

- TOTP secrets are stored in plaintext (required for verification).
  Protect the database with encryption at rest and strict access
  controls.
- Backup codes are stored as SHA-256 hashes (not plaintext).
- Backup code verification uses constant-time comparison to prevent
  timing attacks.
- The `mfa_verified` flag is session-scoped and cleared on logout.
- To add re-authentication for disabling MFA, modify
  `POST /mfa/disable` to verify the user's password (the current
  implementation uses a simple confirmation string for dev mode).
