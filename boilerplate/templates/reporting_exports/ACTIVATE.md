# Reporting & Exports Component — Activation Guide

## What This Component Adds

- `POST /api/exports` — start a new export job (CSV, XLSX, or PDF)
- `GET /api/exports/{id}` — check export job status
- `GET /api/exports/{id}/download` — download completed export
- `ReportService` — multi-backend report generator (CSV, XLSX via openpyxl, PDF via weasyprint)
- `ExportJob` model — tracks export job lifecycle
- `generate_export` Procrastinate task — async file generation

## Prerequisites

Install additional dependencies:

```bash
uv add openpyxl weasyprint
```

> `weasyprint` requires system libraries. On macOS: `brew install pango`. On Ubuntu: `apt install libpango-1.0-0 libpangocairo-1.0-0`.

## Environment Variables

Add to your `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `EXPORT_TEMP_DIR` | No | `./exports` | Directory for generated export files |
| `EXPORT_TTL_HOURS` | No | `24` | Hours before temp files should be cleaned up |

### Example

```bash
EXPORT_TEMP_DIR=./exports
EXPORT_TTL_HOURS=24
```

## Migration

This component adds the `export_jobs` table.
After activation:

```bash
make new-migration  # enter "add export jobs table"
make migrate
```

## Verification

```bash
# Run tests
pytest tests/unit/test_reporting_exports.py -v
```

## Quick Start

```python
from app.components.reporting_exports.service import ReportService

service = ReportService()
data = [{"name": "Alice", "score": 95}, {"name": "Bob", "score": 87}]
filepath = service.generate("csv", data, "scores", columns=["name", "score"])
print(filepath)  # ./exports/scores.csv
```

## File Layout After Activation

```
app/components/reporting_exports/
├── __init__.py          # register() — wires router and tasks
├── api.py               # POST start, GET status, GET download
├── service.py           # ReportService (CSV, XLSX, PDF backends)
├── models.py            # ExportJob
├── schemas.py           # ExportRequest, ExportStatus
└── tasks.py             # generate_export
```
