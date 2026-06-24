from __future__ import annotations

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import CurrentUser, DbDeps
from app.core.auth import extract_claims, get_oidc_client
from app.core.config import settings
from app.core.db import async_session_factory
from app.core.saml import build_saml_client
from app.core.security import hash_token
from app.core.templates import get_jinja_env
from app.services.audit_service import log_event
from app.services.auth_service import (
    handle_saml_acs,
)
from app.services.user_service import (
    create_session,
    revoke_session,
    upsert_user,
)

logger = structlog.get_logger()
router = APIRouter(tags=["auth"])


@router.get("/login")
async def login_get(request: Request):
    """Show login page or redirect to OIDC."""
    # Dev login mode
    if settings.auth_dev_mode and settings.environment == "local":
        env = get_jinja_env()
        template = env.get_template("auth/dev_login.html")
        return HTMLResponse(template.render(request=request))

    # OIDC flow
    client = await get_oidc_client()
    if not client:
        return HTMLResponse(
            "<h1>Auth Not Configured</h1><p>Set OIDC env vars or enable AUTH_DEV_MODE=1.</p>",
            status_code=503,
        )

    redirect_uri = str(request.url_for("auth_callback"))
    auth_url = client.create_authorization_url(redirect_uri)["url"]
    return RedirectResponse(auth_url)


@router.post("/login/dev")
async def login_dev_post(request: Request):
    """Dev-mode login: create a session without OIDC."""
    if not settings.auth_dev_mode or settings.environment != "local":
        return HTMLResponse("Dev login not available", status_code=403)

    form = await request.form()
    email = form.get("email", "dev@local")
    display_name = form.get("display_name", "Dev User")

    async with async_session_factory() as db:
        user = await upsert_user(
            db,
            external_subject_id=f"dev:{email}",
            email=email,
            display_name=display_name,
            auth_provider="dev",
        )
        session_token, session_obj = await create_session(
            db,
            user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            max_age_seconds=settings.session_max_age_seconds,
        )

        await log_event(
            db,
            actor_user_id=user.id,
            action="login",
            target_type="user",
            target_id=str(user.id),
            metadata={"provider": "dev", "email": email},
            ip_address=request.client.host if request.client else None,
            request_id=request.headers.get("X-Request-ID"),
        )

        await db.commit()

    request.session["session_token"] = session_token
    response = RedirectResponse(url="/app", status_code=302)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=settings.session_max_age_seconds,
        samesite="lax",
        secure=settings.environment != "local",
    )
    return response


@router.get("/auth/callback")
async def auth_callback(request: Request):
    """OIDC callback: exchange code, upsert user, set session."""
    client = await get_oidc_client()
    if not client:
        return HTMLResponse("OIDC not configured", status_code=503)

    try:
        token_response = await client.authorize_access_token(request)
    except Exception as e:
        logger.error("oidc_token_exchange_failed", error=str(e))
        return HTMLResponse("Authentication failed", status_code=400)

    id_token = token_response.get("id_token")
    if not id_token:
        return HTMLResponse("No ID token in response", status_code=400)

    claims = extract_claims(
        __import__("authlib.jose")
        .JsonWebToken()
        .decode(
            id_token.encode(),
            client.client_secret or "",
        ),
        settings.auth_oidc_provider,
    )

    async with async_session_factory() as db:
        try:
            user = await upsert_user(
                db,
                external_subject_id=claims["sub"],
                email=claims["email"],
                display_name=claims["name"],
                auth_provider=settings.auth_oidc_provider,
            )
            session_token, session_obj = await create_session(
                db,
                user,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                max_age_seconds=settings.session_max_age_seconds,
            )

            await log_event(
                db,
                actor_user_id=user.id,
                action="login",
                target_type="user",
                target_id=str(user.id),
                metadata={"provider": settings.auth_oidc_provider},
                ip_address=request.client.host if request.client else None,
                request_id=request.headers.get("X-Request-ID"),
            )
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("auth_callback_failed")
            return HTMLResponse("Authentication error", status_code=500)

    request.session["session_token"] = session_token
    response = RedirectResponse(url="/app", status_code=302)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=settings.session_max_age_seconds,
        samesite="lax",
        secure=settings.environment != "local",
    )
    return response


@router.get("/me")
async def get_me(user: CurrentUser):
    """Return the current authenticated user as JSON."""
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "auth_provider": user.auth_provider,
        "is_admin": user.is_admin,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


@router.post("/logout")
async def logout(request: Request, user: CurrentUser, db: DbDeps):
    """Revoke session and clear cookie."""
    session_token = request.session.get("session_token")
    if session_token:
        token_hash = hash_token(session_token)
        await revoke_session(db, user, token_hash)
    await log_event(
        db,
        actor_user_id=user.id,
        action="logout",
        target_type="user",
        target_id=str(user.id),
        ip_address=request.client.host if request.client else None,
        request_id=request.headers.get("X-Request-ID"),
    )
    await db.commit()  # commit still needed since we're writing audit log + session revoke

    request.session.clear()
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_token", path="/")
    return response


# ── SAML ──


@router.get("/login/saml")
async def saml_login(request: Request):
    """Redirect to SAML IdP for authentication."""
    if not settings.auth_saml_enabled:
        return HTMLResponse("SAML not enabled", status_code=404)

    acs_url = str(request.url_for("saml_acs"))
    client = build_saml_client(acs_url=acs_url)
    if not client:
        return HTMLResponse("SAML not configured", status_code=503)

    redirect_url = client.create_login_url()
    return RedirectResponse(redirect_url)


@router.post("/auth/saml/acs")
async def saml_acs(request: Request):
    """SAML Assertion Consumer Service — process IdP response."""
    if not settings.auth_saml_enabled:
        return HTMLResponse("SAML not enabled", status_code=404)

    try:
        claims = await handle_saml_acs(request)
    except ValueError as e:
        logger.error("saml_acs_failed", error=str(e))
        return HTMLResponse("Authentication failed", status_code=400)

    async with async_session_factory() as db:
        try:
            user = await upsert_user(
                db,
                external_subject_id=claims["sub"],
                email=claims["email"],
                display_name=claims["name"],
                auth_provider="saml",
            )
            session_token, session_obj = await create_session(
                db,
                user,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                max_age_seconds=settings.session_max_age_seconds,
            )

            await log_event(
                db,
                actor_user_id=user.id,
                action="login",
                target_type="user",
                target_id=str(user.id),
                metadata={"provider": "saml"},
                ip_address=request.client.host if request.client else None,
                request_id=request.headers.get("X-Request-ID"),
            )
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("saml_acs_upsert_failed")
            return HTMLResponse("Authentication error", status_code=500)

    request.session["session_token"] = session_token
    response = RedirectResponse(url="/app", status_code=302)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=settings.session_max_age_seconds,
        samesite="lax",
        secure=settings.environment != "local",
    )
    return response


@router.get("/auth/saml/metadata")
async def saml_metadata(request: Request):
    """Serve SP metadata XML for IdP registration."""
    if not settings.auth_saml_enabled:
        return HTMLResponse("SAML not enabled", status_code=404)

    acs_url = str(request.url_for("saml_acs"))
    client = build_saml_client(acs_url=acs_url)
    if not client:
        return HTMLResponse("SAML not configured", status_code=503)

    sp_metadata_xml = client.create_sp_metadata()
    return HTMLResponse(sp_metadata_xml, media_type="application/xml")
