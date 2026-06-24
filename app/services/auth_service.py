from __future__ import annotations

import structlog
from authlib.integrations.starlette_client import StarletteOAuth2App
from authlib.oidc.core import CodeIDToken
from starlette.requests import Request

from app.core.auth import get_oidc_client

logger = structlog.get_logger()


async def handle_oidc_callback(
    request: Request,
    client: StarletteOAuth2App,
) -> CodeIDToken:
    """Exchange auth code for tokens and return ID token."""
    token_response = await client.authorize_access_token(request)
    id_token = CodeIDToken(token_response["id_token"])
    return id_token


async def get_login_url(request: Request) -> str | None:
    """Build the OIDC authorization redirect URL."""
    client = await get_oidc_client()
    if not client:
        return None
    redirect_uri = str(request.url_for("auth_callback"))
    return client.create_authorization_url(redirect_uri)["url"]
