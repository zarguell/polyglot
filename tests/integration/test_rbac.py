from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import pytest
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import require_permission
from app.models.role import Role, role_permissions
from app.models.user import User
from app.models.user_role import UserRole
from app.services.rbac_service import (
    create_permission,
    create_role,
    get_user_permissions,
    grant_role,
    has_permission,
    revoke_role,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest.mark.asyncio
async def test_create_role_and_permission(db_session):
    role = await create_role(db_session, name="editor", description="Editor role")
    assert role is not None
    assert role.name == "editor"
    assert role.is_system is False

    perm = await create_permission(
        db_session,
        resource="posts",
        action="edit",
        description="Can edit posts",
    )
    assert perm is not None
    assert perm.resource == "posts"
    assert perm.action == "edit"

    await db_session.execute(
        role_permissions.insert().values(role_id=role.id, permission_id=perm.id),
    )
    await db_session.commit()

    fetched = await db_session.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role.id),
    )
    found = fetched.scalar_one()
    assert len(found.permissions) == 1
    assert found.permissions[0].resource == "posts"


@pytest.mark.asyncio
async def test_grant_and_revoke_role(db_session):
    user = User(
        external_subject_id="test:rbac-user1",
        email="rbac@test.com",
        display_name="RBAC Test",
        auth_provider="test",
    )
    db_session.add(user)
    await db_session.commit()

    role = await create_role(db_session, name="viewer", description="Viewer role")
    assert role is not None

    granted = await grant_role(db_session, user=user, role_id=role.id)
    assert granted is True

    link = await db_session.execute(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id),
    )
    assert link.scalar_one_or_none() is not None

    revoked = await revoke_role(db_session, user=user, role_id=role.id)
    assert revoked is True

    link2 = await db_session.execute(
        select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id),
    )
    assert link2.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_has_permission_via_role(db_session):
    user = User(
        external_subject_id="test:rbac-user2",
        email="rbac2@test.com",
        display_name="RBAC Test 2",
        auth_provider="test",
    )
    db_session.add(user)
    await db_session.commit()

    perm = await create_permission(db_session, resource="audit", action="view")
    assert perm is not None

    role = await create_role(db_session, name="auditor")
    assert role is not None

    await db_session.execute(
        role_permissions.insert().values(role_id=role.id, permission_id=perm.id),
    )
    await db_session.commit()

    await grant_role(db_session, user=user, role_id=role.id)
    await db_session.commit()

    assert await has_permission(db_session, user=user, resource="audit", action="view") is True
    assert await has_permission(db_session, user=user, resource="audit", action="delete") is False
    assert await has_permission(db_session, user=user, resource="users", action="view") is False


@pytest.mark.asyncio
async def test_get_user_permissions(db_session):
    user = User(
        external_subject_id="test:rbac-user3",
        email="rbac3@test.com",
        display_name="RBAC Test 3",
        auth_provider="test",
    )
    db_session.add(user)
    await db_session.commit()

    perm1 = await create_permission(db_session, resource="users", action="view")
    perm2 = await create_permission(db_session, resource="users", action="edit")

    role = await create_role(db_session, name="moderator")
    await db_session.execute(
        role_permissions.insert().values(role_id=role.id, permission_id=perm1.id),
    )
    await db_session.execute(
        role_permissions.insert().values(role_id=role.id, permission_id=perm2.id),
    )
    await db_session.commit()

    await grant_role(db_session, user=user, role_id=role.id)
    await db_session.commit()

    user_perms = await get_user_permissions(db_session, user=user)
    assert len(user_perms) == 2
    resources = {(p.resource, p.action) for p in user_perms}
    assert ("users", "view") in resources
    assert ("users", "edit") in resources


@pytest.mark.asyncio
async def test_require_permission_dependency_grants_access(db_session):
    import base64
    import json

    from httpx import ASGITransport, AsyncClient
    from itsdangerous import TimestampSigner
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.api.deps import get_db
    from app.core.config import settings
    from app.core.security import generate_session_token, hash_token
    from app.main import SESSION_COOKIE_NAME, create_app
    from app.models.auth_session import AuthSession

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def dep_get_db():
        async with session_factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_db] = dep_get_db

    user = User(
        external_subject_id="test:rbac-perm-user1",
        email="rbac-perm1@test.com",
        display_name="RBAC Perm User 1",
        auth_provider="test",
    )
    db_session.add(user)
    await db_session.commit()

    perm = await create_permission(db_session, resource="admin", action="access")
    role = await create_role(db_session, name="superadmin")
    await db_session.execute(
        role_permissions.insert().values(role_id=role.id, permission_id=perm.id),
    )
    await grant_role(db_session, user=user, role_id=role.id)
    await db_session.commit()

    token = generate_session_token()
    token_hash = hash_token(token)
    session_obj = AuthSession(
        user_id=user.id,
        session_token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(seconds=3600),
    )
    db_session.add(session_obj)
    await db_session.commit()

    test_router = APIRouter()

    @test_router.get("/test/granted")
    async def granted_route(
        current_user: Annotated[User, Depends(require_permission("admin", "access"))],
    ):
        return {"ok": True}

    app.include_router(test_router, prefix="/rbac-test")

    session_data = {"session_token": token, "csrf_token": "test-csrf-token"}
    data = base64.b64encode(json.dumps(session_data).encode("utf-8"))
    signer = TimestampSigner(settings.secret_key.get_secret_value())
    signed = signer.sign(data).decode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set(SESSION_COOKIE_NAME, signed)
        ac.headers["X-CSRFToken"] = "test-csrf-token"
        resp = await ac.get("/rbac-test/test/granted")
        assert resp.status_code == 200, f"Unexpected {resp.status_code}: {resp.text}"
        assert resp.json() == {"ok": True}


@pytest.mark.asyncio
async def test_require_permission_dependency_rejects_without_permission(db_session):
    import base64
    import json

    from httpx import ASGITransport, AsyncClient
    from itsdangerous import TimestampSigner
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.api.deps import get_db
    from app.core.config import settings
    from app.core.security import generate_session_token, hash_token
    from app.main import SESSION_COOKIE_NAME, create_app
    from app.models.auth_session import AuthSession

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def dep_get_db():
        async with session_factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_db] = dep_get_db

    user = User(
        external_subject_id="test:rbac-perm-user2",
        email="rbac-perm2@test.com",
        display_name="RBAC Perm User 2",
        auth_provider="test",
    )
    db_session.add(user)
    await db_session.commit()

    token = generate_session_token()
    token_hash = hash_token(token)
    session_obj = AuthSession(
        user_id=user.id,
        session_token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(seconds=3600),
    )
    db_session.add(session_obj)
    await db_session.commit()

    test_router = APIRouter()

    @test_router.get("/test/denied")
    async def denied_route(
        current_user: Annotated[User, Depends(require_permission("super", "power"))],
    ):
        return {"ok": True}

    app.include_router(test_router, prefix="/rbac-test")

    session_data = {"session_token": token, "csrf_token": "test-csrf-token"}
    data = base64.b64encode(json.dumps(session_data).encode("utf-8"))
    signer = TimestampSigner(settings.secret_key.get_secret_value())
    signed = signer.sign(data).decode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.cookies.set(SESSION_COOKIE_NAME, signed)
        ac.headers["X-CSRFToken"] = "test-csrf-token"
        resp = await ac.get("/rbac-test/test/denied")
        assert resp.status_code == 403, f"Unexpected {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_duplicate_role_returns_none(db_session):
    r1 = await create_role(db_session, name="unique-role")
    assert r1 is not None

    r2 = await create_role(db_session, name="unique-role")
    assert r2 is None
