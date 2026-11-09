"""Add transfer_task.stage for in-flight phase display."""

from __future__ import annotations

from alembic import op
from sqlalchemy import Column, String, inspect

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("transfer_task")}
    if "stage" not in columns:
        with op.batch_alter_table("transfer_task") as batch_op:
            batch_op.add_column(Column("stage", String, nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("transfer_task") as batch_op:
        batch_op.drop_column("stage")
