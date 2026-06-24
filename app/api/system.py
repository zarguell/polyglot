from __future__ import annotations

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDeps
from app.core.templates import get_jinja_env
from app.models.installed_component import InstalledComponent
from app.services.rbac_service import count_user_permissions, get_user_roles

logger = structlog.get_logger()
router = APIRouter(tags=["system"])


@router.get("/app", response_class=HTMLResponse)
async def app_shell(
    request: Request,
    user: CurrentUser,
    db: DbDeps,
):
    """Authenticated dashboard shell page."""
    env = get_jinja_env()
    template = env.get_template("app/shell.html")

    result = await db.execute(
        select(InstalledComponent).order_by(InstalledComponent.activated_at.desc()),
    )
    components = result.scalars().all()

    roles = await get_user_roles(db, user=user)
    perm_count = await count_user_permissions(db, user=user)

    return HTMLResponse(
        template.render(
            request=request,
            user=user,
            components=components,
            roles=roles,
            permission_count=perm_count,
        ),
    )
