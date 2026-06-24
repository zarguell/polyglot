"""Reporting & Exports background tasks using Procrastinate."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import structlog

from app.components.reporting_exports.service import ReportService
from app.core.db import async_session_factory
from app.core.tasks import task_app

logger = structlog.get_logger()


@task_app.task(name="reporting_exports.generate_export")
def generate_export(export_job_id: str) -> None:
    """Generate an export file asynchronously.

    Loads the job from the database, generates the report, and updates
    the job record with the file path and completed status.
    """

    async def _run():
        from sqlalchemy import select

        from app.components.reporting_exports.models import ExportJob

        async with async_session_factory() as db:
            result = await db.execute(
                select(ExportJob).where(ExportJob.id == uuid.UUID(export_job_id))
            )
            job = result.scalar_one_or_none()

            if not job:
                logger.error("export_job_not_found", job_id=export_job_id)
                return

            job.status = "processing"
            await db.commit()

            try:
                service = ReportService()
                filepath = service.generate(
                    format=job.format,
                    data=[{"id": 1, "name": "Example", "value": 42}],
                    filename=f"export_{export_job_id}",
                )

                job.file_path = filepath
                job.status = "completed"
                job.completed_at = datetime.now(UTC)
                await db.commit()

                logger.info("export_completed", job_id=export_job_id, filepath=filepath)
            except Exception:
                logger.exception("export_failed", job_id=export_job_id)
                job.status = "failed"
                await db.commit()

    asyncio.run(_run())
