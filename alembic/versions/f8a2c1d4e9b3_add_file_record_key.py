"""add key column to file_records

Revision ID: f8a2c1d4e9b3
Revises: 193dce9455ca
Create Date: 2026-06-24 15:00:00.000000

Adds a URL-safe ``key`` column to ``file_records``. The column is nullable so
existing rows (which addressed files via ``storage_path``) keep working; the
application falls back to ``storage_path`` when ``key`` is NULL.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f8a2c1d4e9b3"
down_revision: str | None = "193dce9455ca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "file_records",
        sa.Column("key", sa.String(length=64), nullable=True),
    )
    op.create_index(op.f("ix_file_records_key"), "file_records", ["key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_file_records_key"), table_name="file_records")
    op.drop_column("file_records", "key")
