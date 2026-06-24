"""Unit tests for LDAP/AD component."""

from __future__ import annotations

import importlib


def test_import_ldap_ad_component():
    """Smoke test: the component module imports cleanly."""
    mod = importlib.import_module("app.components.ldap_ad")
    assert hasattr(mod, "register"), "LDAP/AD component must expose register()"


def test_register_is_callable():
    """register() is a callable function."""
    from app.components.ldap_ad import register

    assert callable(register)
    assert register.__name__ == "register"


def test_ldap_service_not_configured_when_no_env():
    """LDAPService reports not configured when env vars are unset."""
    import os

    # Save and clear LDAP env vars
    saved = {
        k: os.environ.pop(k, None) for k in ["LDAP_SERVER", "LDAP_BIND_DN", "LDAP_BIND_PASSWORD"]
    }

    try:
        from app.components.ldap_ad.service import LDAPService

        service = LDAPService()
        assert service.is_configured() is False
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def test_ldap_service_configured_when_env_set():
    """LDAPService reports configured when all required env vars are set."""
    import os

    os.environ["LDAP_SERVER"] = "ldap://test.example.com"
    os.environ["LDAP_BIND_DN"] = "cn=admin,dc=example,dc=com"
    os.environ["LDAP_BIND_PASSWORD"] = "password"

    try:
        from app.components.ldap_ad.service import LDAPService

        service = LDAPService()
        assert service.is_configured() is True
    finally:
        for k in ["LDAP_SERVER", "LDAP_BIND_DN", "LDAP_BIND_PASSWORD"]:
            os.environ.pop(k, None)


def test_ldap_connect_returns_none_when_not_configured():
    """connect() returns None when the service is not configured."""
    import os

    saved = {
        k: os.environ.pop(k, None) for k in ["LDAP_SERVER", "LDAP_BIND_DN", "LDAP_BIND_PASSWORD"]
    }

    try:
        from app.components.ldap_ad.service import LDAPService

        service = LDAPService()
        conn = service.connect()
        assert conn is None
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


def test_ldap_service_sync_users_not_configured():
    """sync_users returns zero counts when not configured."""
    import os

    saved = {
        k: os.environ.pop(k, None) for k in ["LDAP_SERVER", "LDAP_BIND_DN", "LDAP_BIND_PASSWORD"]
    }

    try:
        from app.components.ldap_ad.service import LDAPService

        service = LDAPService()
        import asyncio

        result = asyncio.run(service.sync_users(None))
        assert result == {"created": 0, "updated": 0, "skipped": 0}
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
