"""Store payloads for standalone queued manual transfers."""

from __future__ import annotations

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS manual_transfer ("
        "task_id INTEGER PRIMARY KEY REFERENCES transfer_task(id) ON DELETE CASCADE, "
        "account_id INTEGER NOT NULL REFERENCES account(id), "
        "share_url TEXT NOT NULL, password TEXT NOT NULL DEFAULT '', file_ids TEXT NOT NULL, "
        "target_dir TEXT NOT NULL, media_id INTEGER REFERENCES media_item(id), "
        "created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_manual_transfer_account_id ON manual_transfer(account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_manual_transfer_media_id ON manual_transfer(media_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS manual_transfer")
