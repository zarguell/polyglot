"""Ticket attachment routes — upload and download files on a ticket.

Extracted from ``ticket_routes`` to keep each route module under the LOC
ceiling.  Shares the ``/api`` prefix and ``tickets`` tag.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDeps
from app.components.file_storage.models import FileRecord
from app.components.file_storage.service import StorageService
from app.models.ticket import Ticket
from app.schemas.ticket import TicketResponse
from app.services import ticket_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["tickets"])

_MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB


def _get_storage_service() -> StorageService:
    from app.core.config import settings

    return StorageService(
        backend=settings.storage_backend,
        local_path=settings.storage_local_path,
        s3_bucket=settings.aws_bucket,
        s3_region=settings.aws_region,
    )


def _to_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse.model_validate(ticket)


@router.post(
    "/tickets/{ticket_id}/attachments",
    response_model=TicketResponse,
    status_code=201,
)
async def upload_attachment(
    ticket_id: uuid.UUID,
    user: CurrentUser,
    db: DbDeps,
    file: UploadFile = File(...),
    service: StorageService = Depends(_get_storage_service),
):
    """Upload an attachment and attach it to a ticket (max 10 MB)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    if file.size is not None and file.size > _MAX_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Attachment exceeds the 10 MB maximum size",
        )

    ticket = await ticket_service.get_ticket(db, ticket_id)
    contents = await file.read()
    if len(contents) > _MAX_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Attachment exceeds the 10 MB maximum size",
        )

    key, checksum = await service.store(
        contents=contents,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
    )

    record = FileRecord(
        user_id=ticket.assigned_agent_id or user.id,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        size=len(contents),
        storage_backend=service.backend_name,
        key=key,
        storage_path=key,
        checksum=checksum,
    )
    db.add(record)

    paths = list(ticket.attachment_paths or [])
    paths.append(key)
    ticket.attachment_paths = paths

    await db.commit()
    await db.refresh(ticket)
    return _to_response(ticket)


@router.get("/tickets/{ticket_id}/attachments/{key}")
async def download_attachment(
    ticket_id: uuid.UUID,  # noqa: ARG001 — scoping only
    key: str,
    user: CurrentUser,  # noqa: ARG001 — auth gate only
    db: DbDeps,
    service: StorageService = Depends(_get_storage_service),
) -> StreamingResponse:
    """Download an attachment by its storage key."""
    result = await db.execute(select(FileRecord).where(FileRecord.key == key))
    record = result.scalar_one_or_none()
    if record is None:
        result = await db.execute(
            select(FileRecord).where(FileRecord.storage_path == key)
        )
        record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    contents = await service.retrieve(record.storage_key, record.storage_backend)
    if contents is None:
        raise HTTPException(status_code=404, detail="Attachment data not found")

    return StreamingResponse(
        content=iter([contents]),
        media_type=record.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{record.filename}"',
        },
    )
