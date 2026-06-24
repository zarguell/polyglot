from __future__ import annotations

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDeps
from app.components.totp_mfa.models import MFADevice
from app.components.totp_mfa.service import (
    generate_backup_codes,
    generate_qr_data_uri,
    generate_totp_secret,
    get_totp_uri,
    hash_backup_code,
    verify_backup_code,
    verify_totp,
)
from app.components.totp_mfa.template_loader import get_component_env
from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter(tags=["mfa"])


# ── Helper ────────────────────────────────────────────────────────────

TOTP_ISSUER = getattr(settings, "totp_issuer", "Polyglot")


def _render(template_name: str, request: Request, **kwargs) -> HTMLResponse:
    """Render a Jinja2 template from the component's template directory."""
    env = get_component_env()
    template = env.get_template(template_name)
    return HTMLResponse(template.render(request=request, **kwargs))


# ── MFA Setup ─────────────────────────────────────────────────────────


@router.get("/mfa/setup")
async def mfa_setup_page(request: Request, user: CurrentUser, db: DbDeps):
    """Render the MFA setup page with QR code and backup codes.

    If the user already has an active MFA device, redirect to status.
    """
    existing = await db.scalar(
        select(MFADevice).where(
            MFADevice.user_id == user.id,
            MFADevice.is_active.is_(True),
        ),
    )
    if existing and existing.verified_at is not None:
        return RedirectResponse(url="/app", status_code=302)

    # Generate fresh secret and backup codes for this setup session
    secret = generate_totp_secret()
    provisioning_uri = get_totp_uri(
        secret=secret,
        email=user.email,
        issuer=TOTP_ISSUER,
    )
    qr_data_uri = generate_qr_data_uri(provisioning_uri)
    backup_codes = generate_backup_codes(count=8)

    # Store secret temporarily in session for the verify step
    # (cleared after successful verification)
    request.session["mfa_pending_secret"] = secret
    request.session["mfa_pending_backup_codes"] = backup_codes

    return _render(
        "mfa_setup.html",
        request,
        user=user,
        secret=secret,
        provisioning_uri=provisioning_uri,
        qr_data_uri=qr_data_uri,
        backup_codes=backup_codes,
        totp_issuer=TOTP_ISSUER,
    )


@router.post("/mfa/verify")
async def mfa_verify_setup(request: Request, user: CurrentUser, db: DbDeps):
    """Verify a TOTP code to complete MFA setup.

    Reads pending secret from session, verifies the code, creates the
    MFADevice record, and marks it as verified.
    """
    form = await request.form()
    code = (form.get("code") or "").strip()

    secret = request.session.get("mfa_pending_secret")
    backup_codes = request.session.get("mfa_pending_backup_codes", [])

    if not secret:
        return _render(
            "mfa_setup.html",
            request,
            user=user,
            error="Setup session expired. Please start over.",
            secret="",
            provisioning_uri="",
            qr_data_uri="",
            backup_codes=[],
            totp_issuer=TOTP_ISSUER,
        )

    if not verify_totp(secret, code):
        return _render(
            "mfa_setup.html",
            request,
            user=user,
            error="Invalid code. Make sure you've scanned the correct QR code and try again.",
            secret=secret,
            provisioning_uri=get_totp_uri(secret, user.email, TOTP_ISSUER),
            qr_data_uri=generate_qr_data_uri(
                get_totp_uri(secret, user.email, TOTP_ISSUER),
            ),
            backup_codes=backup_codes,
            totp_issuer=TOTP_ISSUER,
        )

    # Deactivate any existing MFA devices for this user
    existing_devices = await db.execute(
        select(MFADevice).where(
            MFADevice.user_id == user.id,
            MFADevice.is_active.is_(True),
        ),
    )
    for device in existing_devices.scalars().all():
        device.is_active = False

    # Create verified MFA device
    import datetime

    device = MFADevice(
        user_id=user.id,
        secret=secret,
        is_active=True,
        backup_code_hashes=[hash_backup_code(c) for c in backup_codes],
        verified_at=datetime.datetime.now(datetime.UTC),
    )
    db.add(device)
    await db.commit()

    # Clear pending state from session
    request.session.pop("mfa_pending_secret", None)
    request.session.pop("mfa_pending_backup_codes", None)

    # Mark MFA as verified for this session
    request.session["mfa_verified"] = True

    logger.info("mfa_device_verified", user_id=str(user.id))

    return RedirectResponse(url="/app", status_code=302)


# ── MFA Challenge (post-login) ────────────────────────────────────────


@router.get("/mfa/challenge")
async def mfa_challenge_page(request: Request, user: CurrentUser, db: DbDeps):
    """Render the MFA challenge page (shown after login before /app).

    The user must enter a 6-digit TOTP code or a backup code.
    """
    # If user doesn't have MFA, just redirect to /app
    device = await db.scalar(
        select(MFADevice).where(
            MFADevice.user_id == user.id,
            MFADevice.is_active.is_(True),
        ),
    )
    if not device:
        return RedirectResponse(url="/app", status_code=302)

    return _render(
        "mfa_challenge.html",
        request,
        user=user,
        error=None,
    )


@router.post("/mfa/challenge")
async def mfa_challenge_submit(request: Request, user: CurrentUser, db: DbDeps):
    """Verify a TOTP or backup code to complete MFA challenge.

    After successful verification, sets mfa_verified in session and
    redirects to the originally requested path (or /app).
    """
    form = await request.form()
    code = (form.get("code") or "").strip()

    if not code:
        return _render(
            "mfa_challenge.html",
            request,
            user=user,
            error="Please enter a verification code.",
        )

    device = await db.scalar(
        select(MFADevice).where(
            MFADevice.user_id == user.id,
            MFADevice.is_active.is_(True),
        ),
    )
    if not device:
        return RedirectResponse(url="/app", status_code=302)

    # Try TOTP verification first
    if verify_totp(device.secret, code):
        request.session["mfa_verified"] = True
        return_to = request.session.pop("mfa_return_to", "/app")
        logger.info("mfa_challenge_passed", user_id=str(user.id))
        return RedirectResponse(url=return_to, status_code=302)

    # Try backup code verification
    if verify_backup_code(code, device.backup_code_hashes):
        # Consume the backup code (remove its hash)
        device.backup_code_hashes = [
            h for h in device.backup_code_hashes if h != hash_backup_code(code)
        ]
        await db.commit()

        request.session["mfa_verified"] = True
        return_to = request.session.pop("mfa_return_to", "/app")
        logger.info(
            "mfa_backup_code_used",
            user_id=str(user.id),
            remaining=len(device.backup_code_hashes),
        )
        return RedirectResponse(url=return_to, status_code=302)

    # Code invalid
    return _render(
        "mfa_challenge.html",
        request,
        user=user,
        error="Invalid verification code. Please try again.",
    )


# ── Disable MFA ───────────────────────────────────────────────────────


@router.get("/mfa/disable")
async def mfa_disable_page(request: Request, user: CurrentUser, db: DbDeps):
    """Render the MFA disable confirmation page."""
    device = await db.scalar(
        select(MFADevice).where(
            MFADevice.user_id == user.id,
            MFADevice.is_active.is_(True),
        ),
    )
    if not device:
        return RedirectResponse(url="/mfa/setup", status_code=302)

    return _render(
        "mfa_disable.html",
        request,
        user=user,
        error=None,
    )


@router.post("/mfa/disable")
async def mfa_disable_submit(
    request: Request,
    user: CurrentUser,
    db: DbDeps,
):
    """Disable MFA for the current user.

    Requires password re-authentication (or confirmation in dev mode).
    Soft-deletes all active MFA devices for the user.
    """
    form = await request.form()
    confirmation = (form.get("confirmation") or "").strip()

    # In production, you'd verify the user's password here.
    # For now, the user must type "disable" to confirm.
    if confirmation.lower() != "disable":
        return _render(
            "mfa_disable.html",
            request,
            user=user,
            error="Type 'disable' to confirm.",
        )

    devices = await db.execute(
        select(MFADevice).where(
            MFADevice.user_id == user.id,
            MFADevice.is_active.is_(True),
        ),
    )
    for device in devices.scalars().all():
        device.is_active = False
    await db.commit()

    request.session.pop("mfa_verified", None)
    request.session.pop("mfa_return_to", None)

    logger.info("mfa_disabled", user_id=str(user.id))

    return RedirectResponse(url="/app", status_code=302)


# ── Backup Codes ──────────────────────────────────────────────────────


@router.get("/mfa/backup-codes")
async def mfa_backup_codes_page(request: Request, user: CurrentUser, db: DbDeps):
    """Regenerate backup codes for the current user.

    Requires the user to be MFA-verified in this session.
    """
    if not request.session.get("mfa_verified"):
        return RedirectResponse(url="/mfa/challenge", status_code=302)

    device = await db.scalar(
        select(MFADevice).where(
            MFADevice.user_id == user.id,
            MFADevice.is_active.is_(True),
        ),
    )
    if not device:
        return RedirectResponse(url="/mfa/setup", status_code=302)

    new_codes = generate_backup_codes(count=8)
    device.backup_code_hashes = [hash_backup_code(c) for c in new_codes]
    await db.commit()

    logger.info("mfa_backup_codes_regenerated", user_id=str(user.id))

    return _render(
        "mfa_backup_codes.html",
        request,
        user=user,
        backup_codes=new_codes,
    )


# ── MFA Status (JSON API) ─────────────────────────────────────────────


@router.get("/api/mfa/status")
async def mfa_status(user: CurrentUser, db: DbDeps):
    """Return the current user's MFA status as JSON."""
    device = await db.scalar(
        select(MFADevice).where(
            MFADevice.user_id == user.id,
            MFADevice.is_active.is_(True),
        ),
    )
    if not device:
        return {"enabled": False}

    return {
        "enabled": True,
        "verified_at": device.verified_at.isoformat() if device.verified_at else None,
        "backup_codes_remaining": len(device.backup_code_hashes),
    }
