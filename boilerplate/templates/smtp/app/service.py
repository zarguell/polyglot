"""EmailService — async email delivery via aiosmtplib with Jinja2 templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class EmailService:
    """Async mail sender backed by aiosmtplib.

    Falls back gracefully when SMTP_HOST is not configured: all public
    methods return ``{"status": "not_configured"}`` immediately.
    """

    def __init__(
        self,
        host: str,
        port: int = 587,
        user: str = "",
        password: str = "",
        use_tls: bool = True,
        from_addr: str = "",
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._use_tls = use_tls
        self._from_addr = from_addr

    def is_configured(self) -> bool:
        return bool(self._host)

    async def send(
        self,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
    ) -> dict[str, Any]:
        """Send a plain-text email. Returns status dict."""
        if not self.is_configured():
            return {"status": "not_configured", "detail": "SMTP_HOST not set"}

        try:
            import aiosmtplib  # noqa: I001
            from email.mime.multipart import MIMEMultipart  # noqa: I001
            from email.mime.text import MIMEText  # noqa: I001

            msg = MIMEMultipart("alternative")
            msg["From"] = self._from_addr
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            if html:
                msg.attach(MIMEText(html, "html"))

            await aiosmtplib.send(
                msg,
                hostname=self._host,
                port=self._port,
                username=self._user or None,
                password=self._password or None,
                use_tls=self._use_tls,
            )

            logger.info("email_sent", to=to, subject=subject)
            return {"status": "sent", "to": to}
        except Exception:
            logger.exception("email_send_failed", to=to, subject=subject)
            raise

    async def send_template(
        self,
        to: str,
        subject: str,
        template_name: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Render a Jinja2 template and send as HTML email."""
        if not self.is_configured():
            return {"status": "not_configured", "detail": "SMTP_HOST not set"}

        html = self._render_template(template_name, context or {})
        return await self.send(to=to, subject=subject, body="", html=html)

    def _render_template(self, name: str, context: dict[str, Any]) -> str:
        """Locate and render a Jinja2 email template."""
        import os as _os

        from jinja2 import Environment, FileSystemLoader

        template_dir = Path(__file__).resolve().parent / "templates" / "email"
        if not template_dir.is_dir():
            template_dir = (
                Path(_os.getcwd()) / "app" / "components" / "smtp" / "templates" / "email"
            )

        env = Environment(loader=FileSystemLoader(str(template_dir)))
        tmpl = env.get_template(name)
        return tmpl.render(**context)
