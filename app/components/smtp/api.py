"""SMTP API routes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser
from app.components.smtp.schemas import EmailSchema
from app.components.smtp.service import EmailService

logger = structlog.get_logger()

router = APIRouter(prefix="/api/email", tags=["email"])


def _get_email_service() -> EmailService:
    """Dependency: create EmailService from settings env vars."""
    import os

    return EmailService(
        host=os.getenv("SMTP_HOST", ""),
        port=int(os.getenv("SMTP_PORT", "587")),
        user=os.getenv("SMTP_USER", ""),
        password=os.getenv("SMTP_PASSWORD", ""),
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        from_addr=os.getenv("EMAIL_FROM", ""),
    )


@router.post("/test", tags=["email"])
async def send_test_email(
    email: EmailSchema,
    current_user: CurrentUser,
    service: EmailService = Depends(_get_email_service),
) -> dict[str, str]:
    """Send a test email. Requires authentication."""
    if not service.is_configured():
        logger.warning("smtp_not_configured")
        return {"status": "not_configured", "detail": "SMTP_HOST not set"}

    task_pending = EmailSchema.from_request(email)
    from app.components.smtp.tasks import send_email

    job = send_email.defer(
        to=task_pending.to,
        subject=task_pending.subject,
        body=task_pending.body,
    )

    logger.info(
        "email_queued",
        to=email.to,
        subject=email.subject,
        job_id=str(job),
    )

    return {"status": "queued", "job_id": str(job)}
