"""SMTP background tasks using Procrastinate."""

from __future__ import annotations

import structlog

from app.core.tasks import task_app

logger = structlog.get_logger()


@task_app.task(name="smtp.send_email", retry=3)
def send_email(to: str, subject: str, body: str) -> None:
    """Send an email asynchronously with automatic retry."""
    import asyncio
    import os

    from app.components.smtp.service import EmailService

    service = EmailService(
        host=os.getenv("SMTP_HOST", ""),
        port=int(os.getenv("SMTP_PORT", "587")),
        user=os.getenv("SMTP_USER", ""),
        password=os.getenv("SMTP_PASSWORD", ""),
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        from_addr=os.getenv("EMAIL_FROM", ""),
    )

    if not service.is_configured():
        logger.warning("smtp_task_not_configured")
        return

    async def _send():
        try:
            await service.send(to=to, subject=subject, body=body)
        except Exception:
            logger.exception("smtp_task_failed", to=to, subject=subject)
            raise

    asyncio.run(_send())
