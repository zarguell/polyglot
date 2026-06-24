from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.core.config import settings
from app.main import SESSION_COOKIE_NAME, create_app

# ── SQLite for fast unit/integration tests ──
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test and drop after."""
    from app.models.base import Base

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """FastAPI test client with overridden DB dependency."""
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Direct DB session for test setup/assertions."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, db_session: AsyncSession) -> AsyncClient:
    """Client with a pre-authenticated session via signed session cookie."""
    from app.services.user_service import create_session, upsert_user

    user = await upsert_user(
        db_session,
        external_subject_id="test:user1",
        email="test@example.com",
        display_name="Test User",
        auth_provider="dev",
    )
    token, session_obj = await create_session(db_session, user, max_age_seconds=3600)
    await db_session.commit()

    # Match Starlette's SessionMiddleware signer: TimestampSigner(secret_key)
    import base64
    import json

    from itsdangerous import TimestampSigner

    session_data = {"session_token": token, "csrf_token": "test-csrf-token"}
    data = base64.b64encode(json.dumps(session_data).encode("utf-8"))
    signer = TimestampSigner(settings.secret_key.get_secret_value())
    signed = signer.sign(data).decode("utf-8")
    client.cookies.set(SESSION_COOKIE_NAME, signed)
    # Store CSRF token for test use
    client.headers["X-CSRFToken"] = "test-csrf-token"
    return client
