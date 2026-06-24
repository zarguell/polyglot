from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_healthz(client):
    """Smoke test: health endpoint returns 200."""
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_home_page(client):
    """Public home page renders."""
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_login_redirect(client):
    """Login page returns either HTML (dev mode) or redirect."""
    resp = await client.get("/login", follow_redirects=False)
    # In test environment with no OIDC configured and dev mode off, expect 503
    assert resp.status_code in (200, 302, 503)


@pytest.mark.asyncio
async def test_auth_callback_no_oidc(client):
    """Callback without OIDC configured returns 503."""
    resp = await client.get("/auth/callback?code=test&state=test")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    """/me returns 401 without auth."""
    resp = await client.get("/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(auth_client):
    """/me returns user info when authenticated."""
    resp = await auth_client.get("/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["display_name"] == "Test User"


@pytest.mark.asyncio
async def test_app_shell_authenticated(auth_client):
    """App shell page renders for authenticated user."""
    resp = await auth_client.get("/app")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_logout(auth_client):
    """Logout clears session and redirects."""
    resp = await auth_client.post("/logout", follow_redirects=False)
    assert resp.status_code == 302
    # Check that cookie is cleared
    set_cookie = resp.headers.get("set-cookie", "")
    assert "Max-Age=0" in set_cookie or "expires" in set_cookie.lower()
