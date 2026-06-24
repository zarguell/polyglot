"""LDAP/AD API routes — trigger sync and check status."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser
from app.components.ldap_ad.service import LDAPService
from app.components.ldap_ad.tasks import sync_ldap_users

logger = structlog.get_logger()

router = APIRouter(prefix="/api/ldap", tags=["ldap"])


@router.post("/sync")
async def trigger_ldap_sync(current_user: CurrentUser) -> dict:
    """Trigger a full LDAP user synchronization as a background task."""
    service = LDAPService()
    if not service.is_configured():
        raise HTTPException(status_code=503, detail="LDAP not configured")

    try:
        sync_ldap_users.defer()
    except Exception:
        logger.warning("sync_ldap_users_defer_failed")

    logger.info("ldap_sync_triggered", user_id=str(current_user.id))
    return {"status": "ok", "message": "LDAP sync triggered"}


@router.get("/status")
async def ldap_status(current_user: CurrentUser) -> dict:
    """Check LDAP configuration status."""
    service = LDAPService()
    return {
        "configured": service.is_configured(),
        "server": service._server,
        "base_dn": service._base_dn,
    }
