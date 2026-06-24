"""Reporting & Exports API routes — start, check, and download export jobs."""

from __future__ import annotations

import os
import uuid

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import CurrentUser
from app.components.reporting_exports.models import ExportJob
from app.components.reporting_exports.schemas import ExportRequest, ExportStatus
from app.components.reporting_exports.tasks import generate_export
from app.core.db import async_session_factory

logger = structlog.get_logger()

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.post("")
async def start_export(payload: ExportRequest, current_user: CurrentUser) -> dict:
    """Start a new export job."""
    job = ExportJob(
        id=uuid.uuid4(),
        user_id=str(current_user.id),
        format=payload.format,
        status="pending",
        filters=payload.filters,
    )

    async with async_session_factory() as db:
        db.add(job)
        await db.commit()

    try:
        generate_export.defer(export_job_id=str(job.id))
    except Exception:
        logger.warning("generate_export_defer_failed", export_job_id=str(job.id))

    logger.info("export_job_started", job_id=str(job.id), format=payload.format)
    return {"status": "ok", "id": str(job.id)}


@router.get("/{export_id}")
async def get_export_status(export_id: str, current_user: CurrentUser) -> ExportStatus:
    """Check the status of an export job."""
    async with async_session_factory() as db:
        result = await db.execute(select(ExportJob).where(ExportJob.id == uuid.UUID(export_id)))
        job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    return ExportStatus(
        id=job.id,
        format=job.format,
        status=job.status,
        file_path=job.file_path,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


@router.get("/{export_id}/download")
async def download_export(export_id: str, current_user: CurrentUser) -> FileResponse:
    """Download a completed export file."""
    async with async_session_factory() as db:
        result = await db.execute(select(ExportJob).where(ExportJob.id == uuid.UUID(export_id)))
        job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    if job.status != "completed" or not job.file_path:
        raise HTTPException(status_code=400, detail="Export not yet completed")

    if not os.path.isfile(job.file_path):
        raise HTTPException(status_code=404, detail="Export file not found on disk")

    return FileResponse(
        job.file_path,
        media_type="application/octet-stream",
        filename=os.path.basename(job.file_path),
    )
