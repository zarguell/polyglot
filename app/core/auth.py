from __future__ import annotations

from typing import Any

import structlog
from authlib.integrations.starlette_client import StarletteOAuth2App
from authlib.oidc.core import CodeIDToken

from app.core.config import settings

logger = structlog.get_logger()


PROVIDER_CONFIGS: dict[str, dict[str, Any]] = {
    "generic": {},
    "entra": {
        "discovery_url": "https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration",
    },
    "okta": {
        "discovery_url": "https://{domain}/.well-known/openid-configuration",
    },
    "google": {
        "discovery_url": "https://accounts.google.com/.well-known/openid-configuration",
    },
}


def build_oidc_client() -> StarletteOAuth2App | None:
    """Create an Authlib OIDC client from settings. Returns None if not configured."""
    client_id = settings.auth_oidc_client_id
    client_secret = (
        settings.auth_oidc_client_secret.get_secret_value()
        if settings.auth_oidc_client_secret
        else None
    )
    if not client_id or not client_secret:
        logger.info("auth_missing_credentials", provider=settings.auth_oidc_provider)
        return None

    provider_config = PROVIDER_CONFIGS.get(settings.auth_oidc_provider, {})
    discovery_url = provider_config.get("discovery_url", "")

    if settings.auth_oidc_provider == "generic":
        discovery_url = settings.auth_oidc_discovery_url
    elif settings.auth_oidc_provider == "entra":
        discovery_url = discovery_url.format(tenant=settings.auth_oidc_tenant or "common")
    elif settings.auth_oidc_provider == "okta":
        discovery_url = discovery_url.format(domain=settings.auth_oidc_domain or "dev-okta")

    if not discovery_url:
        logger.warning("auth_no_discovery_url", provider=settings.auth_oidc_provider)
        return None

    client = StarletteOAuth2App(
        client_id=client_id,
        client_secret=client_secret,
        authorize_url="",
        authorize_params=None,
        access_token_url="",
        token_endpoint_auth_method="client_secret_basic",
    )
    client.load_server_metadata(
        __import__("httpx")
        .get(
            str(discovery_url),
            timeout=10,
        )
        .json(),
    )
    return client


def extract_claims(id_token: CodeIDToken, provider: str) -> dict[str, str]:
    """Normalize claims from different OIDC providers into standard fields."""
    if provider == "entra":
        return {
            "sub": id_token.get("oid", id_token["sub"]),
            "email": id_token.get("preferred_username", id_token.get("email", "")),
            "name": id_token.get("name", id_token.get("preferred_username", "")),
        }
    if provider == "google":
        return {
            "sub": id_token["sub"],
            "email": id_token.get("email", ""),
            "name": id_token.get("name", id_token.get("email", "")),
        }
    # generic / okta
    return {
        "sub": id_token["sub"],
        "email": id_token.get("email", ""),
        "name": id_token.get("name", id_token.get("email", "")),
    }


async def get_oidc_client() -> StarletteOAuth2App | None:
    """Async wrapper — currently sync, but here for future asyncio auth."""
    return build_oidc_client()
