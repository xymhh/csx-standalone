"""Add account is_enabled and is_primary, relax unique constraint."""

from __future__ import annotations

from alembic import op
from sqlalchemy import Boolean, Column, inspect

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("account")}
    
    # SQLite 移除 UNIQUE 约束需要重建表或 batch_alter_table
    with op.batch_alter_table("account", recreate="always") as batch_op:
        if "is_enabled" not in columns:
            batch_op.add_column(Column("is_enabled", Boolean, nullable=False, server_default="1"))
        if "is_primary" not in columns:
            batch_op.add_column(Column("is_primary", Boolean, nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("account", recreate="always") as batch_op:
        batch_op.drop_column("is_primary")
        batch_op.drop_column("is_enabled")
