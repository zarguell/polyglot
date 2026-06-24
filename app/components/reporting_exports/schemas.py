"""Reporting & Exports schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ExportRequest(BaseModel):
    """Request to start a new export job."""

    format: str  # csv, xlsx, pdf
    filters: dict | None = None


class ExportStatus(BaseModel):
    """Status of an export job."""

    id: UUID
    format: str
    status: str
    file_path: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
