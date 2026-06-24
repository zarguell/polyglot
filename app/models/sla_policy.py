"""SLAPolicy model — per-priority response/resolution targets."""

from __future__ import annotations

import uuid

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base, uuid_pk


class SLAPolicy(AuditMixin, Base):
    """SLA target for a given priority level.

    Exactly one row per priority value (``low``, ``medium``, ``high``,
    ``critical``).  ``response_time_hours`` is the target first-response time;
    ``resolution_time_hours`` is the target full-resolution time.
    """

    __tablename__ = "sla_policies"

    id: Mapped[uuid.UUID] = uuid_pk()
    priority: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    response_time_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_time_hours: Mapped[int] = mapped_column(Integer, nullable=False)
