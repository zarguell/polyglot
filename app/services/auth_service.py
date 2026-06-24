from __future__ import annotations

import structlog
from authlib.integrations.starlette_client import StarletteOAuth2App
from authlib.oidc.core import CodeIDToken
from starlette.requests import Request

from app.core.auth import get_oidc_client
from app.core.saml import build_saml_client, extract_saml_claims

logger = structlog.get_logger()


async def handle_oidc_callback(
    request: Request,
    client: StarletteOAuth2App,
) -> CodeIDToken:
    """Exchange auth code for tokens and return ID token."""
    token_response = await client.authorize_access_token(request)
    id_token = CodeIDToken(token_response["id_token"])
    return id_token


async def handle_saml_acs(request: Request) -> dict[str, str]:
    """Process SAML assertion from ACS POST and return normalized claims."""
    form = await request.form()
    saml_response_val = form.get("SAMLResponse", "")

    acs_url = str(request.url_for("saml_acs"))
    client = build_saml_client(acs_url=acs_url)
    if not client:
        logger.warning("saml_acs_no_client")
        raise ValueError("SAML client not configured")

    saml_response_str = str(saml_response_val)
    auth_data = client.parse_authn_response(saml_response_str)
    claims = extract_saml_claims(auth_data)

    if not claims["sub"]:
        logger.warning("saml_acs_no_subject")
        raise ValueError("SAML assertion missing NameID")

    return claims


async def get_login_url(request: Request) -> str | None:
    """Build the OIDC authorization redirect URL."""
    client = await get_oidc_client()
    if not client:
        return None
    redirect_uri = str(request.url_for("auth_callback"))
    return client.create_authorization_url(redirect_uri)["url"]
