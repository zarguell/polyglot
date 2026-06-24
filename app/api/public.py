from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.core.config import settings
from app.core.db import check_db_connection
from app.core.templates import get_jinja_env

router = APIRouter(tags=["public"])


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.get("/readyz")
async def readyz():
    db_ok = await check_db_connection()
    if not db_ok:
        return JSONResponse(
            content={"status": "not_ready", "database": "unreachable"},
            status_code=503,
        )
    return {"status": "ready", "database": "connected"}


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    env = get_jinja_env()
    template = env.get_template("public/home.html")
    return HTMLResponse(
        template.render(
            request=request,
            user=getattr(request.state, "user", None),
            saml_enabled=settings.auth_saml_enabled,
        ),
    )
