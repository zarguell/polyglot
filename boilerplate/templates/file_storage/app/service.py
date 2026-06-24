"""StorageService — pluggable local and S3 backends."""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import structlog

logger = structlog.get_logger()


class StorageService:
    """File storage with pluggable backends: local filesystem or S3.

    Falls back gracefully when the selected backend is not configured.
    """

    def __init__(
        self,
        backend: str = "local",
        local_path: str = "./storage",
        s3_bucket: str = "",
        s3_region: str = "us-east-1",
    ) -> None:
        self.backend_name = backend
        self._local_path = Path(local_path)
        self._s3_bucket = s3_bucket
        self._s3_region = s3_region

    async def store(
        self,
        contents: bytes,
        filename: str,
        content_type: str,
    ) -> tuple[str, str]:
        """Store file contents. Returns ``(key, checksum)``.

        ``key`` is a URL-safe identifier (UUID hex) used by :meth:`retrieve`.
        """
        checksum = hashlib.sha256(contents).hexdigest()
        key = uuid.uuid4().hex

        if self.backend_name == "s3":
            await self._store_s3(contents, key, content_type)
        else:
            await self._store_local(contents, key, filename)

        return key, checksum

    async def retrieve(self, key: str, backend: str) -> bytes | None:
        """Retrieve file contents by storage key."""
        if backend == "s3":
            return await self._retrieve_s3(key)
        return await self._retrieve_local(key)

    async def delete(self, key: str, backend: str) -> None:
        """Delete a file from storage by key."""
        if backend == "s3":
            await self._delete_s3(key)
        else:
            await self._delete_local(key)

    # ── Local filesystem backend ──

    async def _store_local(self, contents: bytes, key: str, filename: str) -> None:
        self._local_path.mkdir(parents=True, exist_ok=True)
        file_path = self._local_path / key
        file_path.write_bytes(contents)
        logger.info("file_stored_local", key=key, path=str(file_path), filename=filename)

    async def _retrieve_local(self, key: str) -> bytes | None:
        candidate = self._local_path / key
        if not candidate.exists():
            # Backward compat: legacy records stored the full filesystem path.
            candidate = Path(key)
        if not candidate.exists():
            return None
        return candidate.read_bytes()

    async def _delete_local(self, key: str) -> None:
        candidate = self._local_path / key
        if not candidate.exists():
            candidate = Path(key)
        if candidate.exists():
            candidate.unlink()
            logger.info("file_deleted_local", key=key, path=str(candidate))

    # ── S3 backend (behind env var gate) ──

    async def _store_s3(self, contents: bytes, key: str, content_type: str) -> None:
        import os

        bucket = self._s3_bucket or os.getenv("AWS_BUCKET", "")
        if not bucket:
            raise ValueError("AWS_BUCKET must be set for S3 storage")

        import boto3

        s3 = boto3.client("s3", region_name=self._s3_region)
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=contents,
            ContentType=content_type,
        )
        logger.info("file_stored_s3", bucket=bucket, key=key)

    async def _retrieve_s3(self, key: str) -> bytes | None:
        import os

        bucket = self._s3_bucket or os.getenv("AWS_BUCKET", "")
        if not bucket:
            return None

        import boto3

        s3 = boto3.client("s3", region_name=self._s3_region)
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            return obj["Body"].read()
        except Exception:
            logger.exception("s3_retrieve_failed", key=key)
            return None

    async def _delete_s3(self, key: str) -> None:
        import os

        bucket = self._s3_bucket or os.getenv("AWS_BUCKET", "")
        if not bucket:
            return

        import boto3

        s3 = boto3.client("s3", region_name=self._s3_region)
        s3.delete_object(Bucket=bucket, Key=key)
        logger.info("file_deleted_s3", bucket=bucket, key=key)
