"""Add account display name."""

from __future__ import annotations

from alembic import op
from sqlalchemy import Column, String, inspect

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("account")}
    if "name" not in columns:
        op.add_column("account", Column("name", String, nullable=False, server_default=""))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("account")}
    if "name" in columns:
        op.drop_column("account", "name")
