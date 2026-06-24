#!/usr/bin/env python3
"""Optional seed script for local development. Creates sample data."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.core.db import async_session_factory
from app.models.audit_log import AuditLog
from app.models.installed_component import InstalledComponent
from app.models.user import User


async def seed() -> None:
    async with async_session_factory() as db:
        # Check if data already exists
        from sqlalchemy import func, select

        count = await db.scalar(select(func.count(User.id)))
        if count and count > 0:
            print("Database already seeded, skipping.")
            return

        # Create dev admin user
        user = User(
            external_subject_id="seed:admin",
            email="admin@polyglot.local",
            display_name="Admin",
            auth_provider="seed",
            is_active=True,
            is_admin=True,
            last_login_at=datetime.now(UTC),
        )
        db.add(user)
        await db.flush()

        # Audit log entries
        for action in ["login", "seed_script"]:
            db.add(
                AuditLog(
                    actor_user_id=user.id,
                    action=action,
                    metadata_={"source": "seed"},
                )
            )

        # Sample component registry entries
        for name in ["webhooks", "reporting"]:
            db.add(
                InstalledComponent(
                    name=name,
                    version="0.1.0",
                )
            )

        await db.commit()
        print("Seed data created successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
