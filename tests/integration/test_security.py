from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_security_headers(client):
    """Every response carries security headers."""
    resp = await client.get("/healthz")
    headers = resp.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "content-security-policy" in headers
    assert "frame-ancestors 'none'" in headers["content-security-policy"]


@pytest.mark.asyncio
async def test_csrf_protection(client):
    """POST without CSRF token is rejected."""
    resp = await client.post("/logout")
    assert resp.status_code == 403
    assert "CSRF" in resp.text


@pytest.mark.asyncio
async def test_csrf_token_in_session(client):
    """GET request seeds a CSRF token in the session."""
    resp = await client.get("/")
    cookie = resp.cookies.get("polyglot_session")
    assert cookie is not None
