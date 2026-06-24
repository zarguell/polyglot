from __future__ import annotations

import sqlite3

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.user import User


@pytest.mark.asyncio
async def test_create_user(db_session):
    """Can create and retrieve a user."""
    user = User(
        external_subject_id="test:create1",
        email="create@test.com",
        display_name="Create Test",
        auth_provider="test",
    )
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(
        select(User).where(User.external_subject_id == "test:create1"),
    )
    found = result.scalar_one()
    assert found.email == "create@test.com"
    assert found.display_name == "Create Test"


@pytest.mark.asyncio
async def test_user_unique_email(db_session):
    """Duplicate email raises integrity error."""
    user1 = User(
        external_subject_id="test:dup1",
        email="dup@test.com",
        display_name="Dup One",
        auth_provider="test",
    )
    db_session.add(user1)
    await db_session.commit()

    user2 = User(
        external_subject_id="test:dup2",
        email="dup@test.com",
        display_name="Dup Two",
        auth_provider="test",
    )
    db_session.add(user2)
    with pytest.raises((IntegrityError, sqlite3.IntegrityError)):
        await db_session.commit()
