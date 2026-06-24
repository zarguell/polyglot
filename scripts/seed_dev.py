#!/usr/bin/env python3
"""Optional seed script for local development. Creates sample data."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from app.core.db import async_session_factory
from app.models.audit_log import AuditLog
from app.models.installed_component import InstalledComponent
from app.models.role import Permission, Role
from app.models.sla_policy import SLAPolicy
from app.models.ticket import Ticket
from app.models.ticket_comment import TicketComment
from app.models.user import User
from app.models.user_role import UserRole


async def seed() -> None:
    async with async_session_factory() as db:
        # Check if data already exists
        from sqlalchemy import func, select

        count = await db.scalar(select(func.count(User.id)))
        if count and count > 0:
            print("Database already seeded, skipping.")
            return

        # Create default RBAC permissions
        default_permissions = [
            ("admin", "access", "Full administrative access"),
            ("users", "manage", "Create, update, delete users"),
            ("users", "view", "View user details"),
            ("roles", "manage", "Create, update, delete roles"),
            ("audit", "view", "View audit logs"),
            ("settings", "edit", "Modify application settings"),
        ]
        perm_map: dict[str, Permission] = {}
        for resource, action, description in default_permissions:
            perm = Permission(resource=resource, action=action, description=description)
            db.add(perm)
            perm_map[f"{resource}:{action}"] = perm
        await db.flush()

        # Create default roles
        admin_role = Role(
            name="admin",
            description="Full system administrator",
            is_system=True,
        )
        admin_role.permissions = list(perm_map.values())

        user_role = Role(
            name="user",
            description="Standard authenticated user",
            is_system=True,
        )
        user_role.permissions = [perm_map["users:view"]]

        db.add_all([admin_role, user_role])
        await db.flush()

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

        # Assign admin role to the seed admin user
        db.add(UserRole(user_id=user.id, role_id=admin_role.id))
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

        # ── Ticket system seed data ────────────────────────────────────

        # SLA policies
        sla_standard = SLAPolicy(
            priority="standard",
            response_time_hours=24,
            resolution_time_hours=72,
        )
        sla_critical = SLAPolicy(
            priority="critical",
            response_time_hours=4,
            resolution_time_hours=24,
        )
        db.add_all([sla_standard, sla_critical])
        await db.flush()

        # Sample tickets across varied statuses
        now = datetime.now(UTC)
        tickets = [
            Ticket(
                customer_email="alice@example.com",
                customer_name="Alice Johnson",
                subject="Login page not loading after update",
                description="Since the latest deployment, the login page shows a blank white screen"
                " in Chrome. Works in incognito mode. Clearing cache did not help.",
                status="open",
                priority="high",
                created_at=now - timedelta(hours=2),
            ),
            Ticket(
                customer_email="bob@example.com",
                customer_name="Bob Smith",
                subject="Need API access for our engineering team",
                description="Our team of 5 engineers needs API keys for the reporting endpoints. "
                "We need read access to /api/v1/reports/* and /api/v1/metrics/*.",
                status="in_progress",
                priority="medium",
                assigned_agent_id=user.id,
                created_at=now - timedelta(days=1),
            ),
            Ticket(
                customer_email="carol@example.com",
                customer_name="Carol Davis",
                subject="Export button returns 500 error",
                description="Clicking the 'Export to CSV' button on the dashboard returns a 500 "
                "Internal Server Error. This started happening this morning and affects all "
                "export formats.",
                status="in_progress",
                priority="high",
                assigned_agent_id=user.id,
                created_at=now - timedelta(hours=6),
            ),
            Ticket(
                customer_email="dave@example.com",
                customer_name="Dave Wilson",
                subject="Password reset email not received",
                description="I have tried resetting my password three times but never receive "
                "the email. Checked spam folder. Can you trigger a manual reset?",
                status="resolved",
                priority="medium",
                assigned_agent_id=user.id,
                resolved_at=now - timedelta(hours=3),
                created_at=now - timedelta(days=2),
            ),
            Ticket(
                customer_email="eve@example.com",
                customer_name="Eve Martinez",
                subject="Billing invoice for June is incorrect",
                description="The invoice for June shows a charge of $299 but my plan should be "
                "$199 per month. The upgrade to pro was applied on May 15th.",
                status="closed",
                priority="low",
                assigned_agent_id=user.id,
                resolved_at=now - timedelta(days=3),
                closed_at=now - timedelta(days=1),
                created_at=now - timedelta(days=5),
            ),
            Ticket(
                customer_email="frank@example.com",
                customer_name="Frank Lee",
                subject="System down — cannot access any pages",
                description="Getting 502 Bad Gateway errors on all pages since 9:00 AM. This is "
                "blocking our entire team from working. Please escalate urgently.",
                status="open",
                priority="critical",
                created_at=now - timedelta(minutes=30),
            ),
        ]
        db.add_all(tickets)
        await db.flush()

        # Ticket comments
        comments = [
            TicketComment(
                ticket_id=tickets[1].id,
                author_id=user.id,
                body="I have generated API keys for Bob's team and attached them to this ticket. "
                "Keys are scoped to read-only access on reporting endpoints as requested.",
                is_internal=False,
            ),
            TicketComment(
                ticket_id=tickets[2].id,
                author_id=user.id,
                body="Stack trace points to the CSV serializer in app/services/exports.py."
                " Investigating the encoding edge case now.",
                is_internal=True,
            ),
            TicketComment(
                ticket_id=tickets[3].id,
                author_id=user.id,
                body="Password reset was triggered manually. User confirmed they received the "
                "email and were able to log in successfully.",
                is_internal=False,
            ),
        ]
        db.add_all(comments)

        await db.commit()
        print("Seed data created successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
