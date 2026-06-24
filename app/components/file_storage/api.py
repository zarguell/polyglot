"""File storage API routes — upload, download, delete."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDeps
from app.components.file_storage.models import FileRecord
from app.components.file_storage.schemas import FileUploadResponse
from app.components.file_storage.service import StorageService

logger = structlog.get_logger()

router = APIRouter(prefix="/api/files", tags=["files"])


def _get_storage_service() -> StorageService:
    import os

    backend = os.getenv("STORAGE_BACKEND", "local")
    return StorageService(
        backend=backend,
        local_path=os.getenv("STORAGE_LOCAL_PATH", "./storage"),
        s3_bucket=os.getenv("AWS_BUCKET", ""),
        s3_region=os.getenv("AWS_REGION", "us-east-1"),
    )


@router.post("/upload", status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    db: DbDeps = Depends(),
    current_user: CurrentUser = Depends(),
    service: StorageService = Depends(_get_storage_service),
) -> FileUploadResponse:
    """Upload a file. Returns metadata including the file ID."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    contents = await file.read()
    storage_path, checksum = await service.store(
        contents=contents,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
    )

    record = FileRecord(
        user_id=current_user.id,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        size=len(contents),
        storage_backend=service.backend_name,
        storage_path=storage_path,
        checksum=checksum,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.info("file_uploaded", file_id=str(record.id), filename=file.filename)

    return FileUploadResponse(
        id=str(record.id),
        filename=record.filename,
        content_type=record.content_type,
        size=record.size,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


@router.get("/{file_id}/download")
async def download_file(
    file_id: uuid.UUID,
    db: DbDeps = Depends(),
    current_user: CurrentUser = Depends(),
    service: StorageService = Depends(_get_storage_service),
) -> StreamingResponse:
    """Download a file by ID."""
    result = await db.execute(select(FileRecord).where(FileRecord.id == file_id))
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    contents = await service.retrieve(record.storage_path, record.storage_backend)
    if contents is None:
        raise HTTPException(status_code=404, detail="File data not found")

    return StreamingResponse(
        content=iter([contents]),
        media_type=record.content_type,
        headers={"Content-Disposition": f'attachment; filename="{record.filename}"'},
    )


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: uuid.UUID,
    db: DbDeps = Depends(),
    current_user: CurrentUser = Depends(),
    service: StorageService = Depends(_get_storage_service),
) -> None:
    """Delete a file. Only the owner or an admin may delete."""
    result = await db.execute(select(FileRecord).where(FileRecord.id == file_id))
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    if record.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this file")

    await service.delete(record.storage_path, record.storage_backend)
    await db.delete(record)
    await db.commit()

    logger.info("file_deleted", file_id=str(file_id))
