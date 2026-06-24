"""Unit tests for Reporting & Exports component."""

from __future__ import annotations

import importlib
import os
import tempfile

import pytest


def test_import_reporting_exports_component():
    """Smoke test: the component module imports cleanly."""
    mod = importlib.import_module("app.components.reporting_exports")
    assert hasattr(mod, "register"), "Reporting exports component must expose register()"


def test_register_is_callable():
    """register() is a callable function."""
    from app.components.reporting_exports import register

    assert callable(register)
    assert register.__name__ == "register"


def test_export_request_schema():
    """ExportRequest schema defaults and validation."""
    from app.components.reporting_exports.schemas import ExportRequest

    req = ExportRequest(format="csv")
    assert req.format == "csv"
    assert req.filters is None

    req2 = ExportRequest(format="xlsx", filters={"date_from": "2024-01-01"})
    assert req2.filters == {"date_from": "2024-01-01"}


def test_report_service_csv_generation():
    """ReportService generates a CSV file from list-of-dict data."""
    from app.components.reporting_exports.service import ReportService

    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReportService(temp_dir=tmpdir)
        data = [
            {"name": "Alice", "score": 95},
            {"name": "Bob", "score": 87},
        ]
        filepath = service.generate("csv", data, "test_report", columns=["name", "score"])

        assert os.path.isfile(filepath)
        assert filepath.endswith(".csv")


def test_report_service_xlsx_generation():
    """ReportService generates an XLSX file."""
    from app.components.reporting_exports.service import ReportService

    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReportService(temp_dir=tmpdir)
        data = [
            {"name": "Alice", "score": 95},
            {"name": "Bob", "score": 87},
        ]
        filepath = service.generate("xlsx", data, "test_report", columns=["name", "score"])

        assert os.path.isfile(filepath)
        assert filepath.endswith(".xlsx")


def test_report_service_pdf_generation():
    """ReportService generates a PDF file via WeasyPrint."""
    try:
        from weasyprint import HTML  # noqa: F401
    except Exception:
        pytest.skip("WeasyPrint system libraries (pango, cairo) not available on this machine")

    from app.components.reporting_exports.service import ReportService

    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReportService(temp_dir=tmpdir)
        data = [
            {"name": "Alice", "score": 95},
            {"name": "Bob", "score": 87},
        ]
        filepath = service.generate("pdf", data, "test_report", columns=["name", "score"])

        assert os.path.isfile(filepath)
        assert filepath.endswith(".pdf")


def test_report_service_invalid_format_raises():
    """ReportService rejects unsupported formats."""
    from app.components.reporting_exports.service import ReportService

    with tempfile.TemporaryDirectory() as tmpdir:
        service = ReportService(temp_dir=tmpdir)
        with pytest.raises(ValueError, match="Unsupported format"):
            service.generate("json", [], "test", columns=[])
