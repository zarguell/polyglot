"""LDAPService — wraps ldap3 for user synchronization with async wrappers."""

from __future__ import annotations

import os
from typing import Any

import structlog
from ldap3 import ALL, Connection, Server, Tls

logger = structlog.get_logger()


class LDAPService:
    """LDAP/Active Directory connector for user synchronization.

    Connects to an LDAP server (AD or generic), searches for users, and
    syncs them into the local User table.
    """

    def __init__(self) -> None:
        self._server = os.getenv("LDAP_SERVER", "")
        self._port = int(os.getenv("LDAP_PORT", "389"))
        self._use_tls = os.getenv("LDAP_USE_TLS", "true").lower() == "true"
        self._bind_dn = os.getenv("LDAP_BIND_DN", "")
        self._bind_password = os.getenv("LDAP_BIND_PASSWORD", "")
        self._base_dn = os.getenv("LDAP_BASE_DN", "")
        self._user_filter = os.getenv("LDAP_USER_FILTER", "(objectClass=person)")

    def is_configured(self) -> bool:
        return bool(self._server and self._bind_dn and self._bind_password)

    def connect(self) -> Connection | None:
        """Establish an LDAP connection and bind."""
        if not self.is_configured():
            logger.warning("ldap_not_configured")
            return None

        try:
            tls = None
            if self._use_tls:
                tls = Tls(validate=False)

            server = Server(
                self._server,
                port=self._port,
                use_ssl=self._use_tls,
                tls=tls,
                get_info=ALL,
            )
            conn = Connection(
                server,
                user=self._bind_dn,
                password=self._bind_password,
                auto_bind=True,
            )
            return conn
        except Exception:
            logger.exception("ldap_connection_failed", server=self._server)
            return None

    def search_users(
        self,
        conn: Connection,
        attributes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for users in the LDAP directory.

        Returns a list of dicts with standard attributes: email, name,
        username, etc.
        """
        if attributes is None:
            attributes = ["cn", "mail", "sAMAccountName", "displayName", "givenName", "sn", "uid"]

        conn.search(
            search_base=self._base_dn,
            search_filter=self._user_filter,
            attributes=attributes,
        )

        users = []
        for entry in conn.entries:
            entry_json = entry.entry_to_json()
            import json

            entry_dict = json.loads(entry_json)
            users.append(entry_dict.get("attributes", {}))

        logger.info("ldap_users_searched", count=len(users))
        return users

    async def sync_users(self, db_session) -> dict[str, int]:
        """Sync LDAP users into the local database.

        Returns counts: {created: N, updated: N, skipped: N}.
        """
        if not self.is_configured():
            return {"created": 0, "updated": 0, "skipped": 0}

        conn = self.connect()
        if not conn:
            return {"created": 0, "updated": 0, "skipped": 0}

        try:
            ldap_users = self.search_users(conn)
            return await self._upsert_users(db_session, ldap_users)
        finally:
            conn.unbind()

    async def _upsert_users(self, db_session, ldap_users: list[dict[str, Any]]) -> dict[str, int]:
        """Insert or update local User records from LDAP results."""
        import uuid

        from sqlalchemy import select

        from app.models.user import User

        created = 0
        updated = 0
        skipped = 0

        for ldap_user in ldap_users:
            email = ldap_user.get("mail", "")
            if not email:
                skipped += 1
                continue

            result = await db_session.execute(select(User).where(User.email == email))
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing user's display name
                display_name = ldap_user.get("displayName", "") or ldap_user.get("cn", "")
                if display_name and existing.display_name != display_name:
                    existing.display_name = display_name
                    updated += 1
                else:
                    skipped += 1
            else:
                # Create new user
                user = User(
                    id=uuid.uuid4(),
                    email=email,
                    display_name=ldap_user.get("displayName", "") or ldap_user.get("cn", email),
                )
                db_session.add(user)
                created += 1

        await db_session.commit()
        logger.info("ldap_sync_complete", created=created, updated=updated, skipped=skipped)
        return {"created": created, "updated": updated, "skipped": skipped}
