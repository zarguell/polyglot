"""File storage schemas."""

from __future__ import annotations

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    """Returned after a successful file upload."""

    id: str
    filename: str
    content_type: str
    size: int
    created_at: str | None = None


class FileDownloadResponse(BaseModel):
    """Metadata returned with a file download."""

    id: str
    filename: str
    content_type: str
    size: int
