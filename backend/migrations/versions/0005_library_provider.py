"""Record the drive provider for STRM direct-link resolution."""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("library_file")}
    if "provider" not in columns:
        op.execute("ALTER TABLE library_file ADD COLUMN provider VARCHAR(32)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_strm_record_library_file_id "
        "ON strm_record(library_file_id)"
    )


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("library_file")}
    if "provider" in columns:
        op.execute("DROP INDEX IF EXISTS uq_strm_record_library_file_id")
        op.drop_column("library_file", "provider")
