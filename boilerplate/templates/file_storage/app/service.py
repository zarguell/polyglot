"""StorageService — pluggable local and S3 backends."""

from __future__ import annotations

import hashlib
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
        content_type: str,  # noqa: ARG002 (reserved for future use)
    ) -> tuple[str, str]:
        """Store file contents. Returns (storage_path, checksum)."""
        checksum = hashlib.sha256(contents).hexdigest()

        if self.backend_name == "s3":
            storage_path = await self._store_s3(contents, filename, checksum)
        else:
            storage_path = await self._store_local(contents, filename, checksum)

        return storage_path, checksum

    async def retrieve(self, storage_path: str, backend: str) -> bytes | None:
        """Retrieve file contents by storage path."""
        if backend == "s3":
            return await self._retrieve_s3(storage_path)
        return await self._retrieve_local(storage_path)

    async def delete(self, storage_path: str, backend: str) -> None:
        """Delete a file from storage."""
        if backend == "s3":
            await self._delete_s3(storage_path)
        else:
            await self._delete_local(storage_path)

    # ── Local filesystem backend ──

    async def _store_local(self, contents: bytes, filename: str, checksum: str) -> str:
        self._local_path.mkdir(parents=True, exist_ok=True)
        file_path = self._local_path / f"{checksum}_{filename}"
        file_path.write_bytes(contents)
        logger.info("file_stored_local", path=str(file_path))
        return str(file_path)

    async def _retrieve_local(self, storage_path: str) -> bytes | None:
        path = Path(storage_path)
        if not path.exists():
            return None
        return path.read_bytes()

    async def _delete_local(self, storage_path: str) -> None:
        path = Path(storage_path)
        if path.exists():
            path.unlink()
            logger.info("file_deleted_local", path=str(path))

    # ── S3 backend (behind env var gate) ──

    async def _store_s3(self, contents: bytes, filename: str, checksum: str) -> str:
        import os

        bucket = self._s3_bucket or os.getenv("AWS_BUCKET", "")
        if not bucket:
            raise ValueError("AWS_BUCKET must be set for S3 storage")

        import boto3

        s3 = boto3.client("s3", region_name=self._s3_region)
        key = f"{checksum}/{filename}"
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=contents,
        )
        logger.info("file_stored_s3", bucket=bucket, key=key)
        return key

    async def _retrieve_s3(self, storage_path: str) -> bytes | None:
        import os

        bucket = self._s3_bucket or os.getenv("AWS_BUCKET", "")
        if not bucket:
            return None

        import boto3

        s3 = boto3.client("s3", region_name=self._s3_region)
        try:
            obj = s3.get_object(Bucket=bucket, Key=storage_path)
            return obj["Body"].read()
        except Exception:
            logger.exception("s3_retrieve_failed", key=storage_path)
            return None

    async def _delete_s3(self, storage_path: str) -> None:
        import os

        bucket = self._s3_bucket or os.getenv("AWS_BUCKET", "")
        if not bucket:
            return

        import boto3

        s3 = boto3.client("s3", region_name=self._s3_region)
        s3.delete_object(Bucket=bucket, Key=storage_path)
        logger.info("file_deleted_s3", bucket=bucket, key=storage_path)
