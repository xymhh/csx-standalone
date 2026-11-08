"""Add transfer_path and media_path to account table."""

from __future__ import annotations

from alembic import op
from sqlalchemy import Column, String, inspect

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in inspect(bind).get_columns("account")}
    with op.batch_alter_table("account") as batch_op:
        if "transfer_path" not in columns:
            batch_op.add_column(
                Column("transfer_path", String, nullable=False, server_default="/CSX/_inbox")
            )
        if "media_path" not in columns:
            batch_op.add_column(
                Column("media_path", String, nullable=False, server_default="/CSX/媒体库")
            )


def downgrade() -> None:
    with op.batch_alter_table("account") as batch_op:
        batch_op.drop_column("media_path")
        batch_op.drop_column("transfer_path")
