# File Storage Component — Activation Guide

## What This Component Adds

- `POST /api/files/upload` — upload a file (authenticated)
- `GET /api/files/{id}/download` — download a file by ID
- `DELETE /api/files/{id}` — delete a file (owner or admin)
- `StorageService` — pluggable backend (LocalStorage, S3)
- `FileRecord` model — metadata: filename, size, checksum, backend, path

## Prerequisites

Install additional dependencies:

```bash
# For local storage only (no extra deps — uses aiofiles which is already installed)

# For S3 backend:
uv add boto3 botocore
```

## Environment Variables

Add to your `.env` file:

| Variable | Required | Default | Description |
|---|---|---|---|
| `STORAGE_BACKEND` | Yes | `local` | `local` or `s3` |
| `STORAGE_LOCAL_PATH` | No | `./storage` | Local filesystem path (local backend) |
| `AWS_ACCESS_KEY_ID` | S3 only | — | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | S3 only | — | AWS secret key |
| `AWS_BUCKET` | S3 only | — | S3 bucket name |
| `AWS_REGION` | S3 only | `us-east-1` | AWS region |

### Example (local development)

```bash
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=./storage
```

### Example (S3 production)

```bash
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_BUCKET=my-app-uploads
AWS_REGION=us-west-2
```

## Migration

This component adds a `file_records` table. After activation:

```bash
make new-migration  # enter "add file_records table"
make migrate
```

## Verification

```bash
# Run tests
pytest tests/unit/test_file_storage.py -v

# Upload a file via API (requires auth)
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@/path/to/test.txt"
```

## File Layout After Activation

```
app/components/file_storage/
├── __init__.py          # register() — wires router
├── api.py               # POST upload, GET download, DELETE
├── service.py           # StorageService with backends
├── models.py            # FileRecord model
└── schemas.py           # FileUploadResponse, FileDownloadResponse
```
