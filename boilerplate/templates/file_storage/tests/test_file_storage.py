"""Unit tests for File Storage component."""

from __future__ import annotations

import asyncio
import importlib


def test_import_file_storage_component():
    """Smoke test: the component module imports cleanly."""
    mod = importlib.import_module("app.components.file_storage")
    assert hasattr(mod, "register"), "File storage component must expose register()"


def test_storage_service_local_store_and_retrieve(tmp_path):
    """LocalStorageBackend stores and retrieves files on disk."""
    from app.components.file_storage.service import StorageService

    service = StorageService(backend="local", local_path=str(tmp_path / "storage"))

    async def _run():
        key, checksum = await service.store(
            contents=b"hello world",
            filename="test.txt",
            content_type="text/plain",
        )
        assert len(key) == 32  # uuid4 hex is URL-safe and 32 chars
        data = await service.retrieve(key, "local")
        assert data == b"hello world"
        await service.delete(key, "local")
        data_after = await service.retrieve(key, "local")
        assert data_after is None

    asyncio.run(_run())


def test_storage_service_checksum():
    """StorageService generates consistent SHA-256 checksums."""
    from app.components.file_storage.service import StorageService

    service = StorageService(backend="local", local_path="/tmp/_fs_test")

    async def _run():
        _, c1 = await service.store(b"same data", "a.txt", "text/plain")
        _, c2 = await service.store(b"same data", "b.txt", "text/plain")
        _, c3 = await service.store(b"different", "c.txt", "text/plain")
        assert c1 == c2
        assert c1 != c3

    asyncio.run(_run())


def test_file_record_module_imports():
    """FileRecord model module imports without cycling."""
    mod = importlib.import_module("app.components.file_storage.models")
    assert hasattr(mod, "FileRecord"), "models module must expose FileRecord"


def test_file_upload_response_schema():
    """FileUploadResponse accepts valid data."""
    from app.components.file_storage.schemas import FileUploadResponse

    resp = FileUploadResponse(
        id="550e8400-e29b-41d4-a716-446655440000",
        filename="test.txt",
        content_type="text/plain",
        size=11,
    )
    assert resp.id == "550e8400-e29b-41d4-a716-446655440000"
    assert resp.filename == "test.txt"


def test_register_is_callable():
    """register() is a callable function."""
    from app.components.file_storage import register

    assert callable(register)
    assert register.__name__ == "register"
