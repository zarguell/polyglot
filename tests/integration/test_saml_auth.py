from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.config import settings


@pytest.mark.asyncio
async def test_saml_metadata_disabled(client):
    """Given SAML disabled, GET /auth/saml/metadata returns 404."""
    resp = await client.get("/auth/saml/metadata")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_saml_acs_disabled(client):
    """Given SAML disabled, POST /auth/saml/acs returns 404."""
    resp = await client.post("/auth/saml/acs", data={"SAMLResponse": "fake"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_saml_login_disabled(client):
    """Given SAML disabled, GET /login/saml returns 404."""
    resp = await client.get("/login/saml", follow_redirects=False)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_saml_metadata_returns_xml(client):
    """Given SAML enabled with a mocked client, GET /auth/saml/metadata returns XML."""
    with (
        patch.object(settings, "auth_saml_enabled", True),
        patch.object(settings, "auth_saml_idp_metadata_url", "https://idp.example.com/metadata"),
        patch.object(settings, "auth_saml_sp_entity_id", "polyglot-test"),
        patch("app.api.auth.build_saml_client") as mock_build,
    ):
        fake_client = _FakeSAMLClient()
        mock_build.return_value = fake_client

        resp = await client.get("/auth/saml/metadata")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/xml"
        assert fake_client.metadata_generated


class _FakeSAMLClient:
    def __init__(self):
        self.metadata_generated = False

    def create_sp_metadata(self) -> str:
        self.metadata_generated = True
        return (
            '<?xml version="1.0"?>'
            "<md:EntityDescriptor"
            ' xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"'
            ' entityID="polyglot-test"/>'
        )

    def create_login_url(self) -> str:
        return "https://idp.example.com/sso?SAMLRequest=fake"

    def parse_authn_response(self, saml_response: str) -> dict:
        _ = saml_response
        return {
            "name_id": "user@example.com",
            "attributes": {
                "email": ["user@example.com"],
                "displayName": ["SAML User"],
            },
        }
