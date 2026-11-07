"""Store quality bucket for library files."""

from __future__ import annotations

from alembic import op
from sqlalchemy import Column, String, inspect

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("library_file")}
    if "quality_bucket" not in columns:
        op.add_column(
            "library_file",
            Column("quality_bucket", String, nullable=False, server_default="sd"),
        )


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("library_file")}
    if "quality_bucket" in columns:
        op.drop_column("library_file", "quality_bucket")
