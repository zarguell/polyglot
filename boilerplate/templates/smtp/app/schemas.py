"""Email schemas for SMTP component."""

from __future__ import annotations

from pydantic import BaseModel


class EmailSchema(BaseModel):
    """Request schema for sending an email."""

    to: str
    subject: str
    body: str
    template: str | None = None
    context: dict[str, str] | None = None

    @classmethod
    def from_request(cls, email: EmailSchema) -> EmailSchema:
        """Return a copy suitable for task serialization."""
        return cls(
            to=email.to,
            subject=email.subject,
            body=email.body,
            template=email.template,
            context=email.context,
        )
