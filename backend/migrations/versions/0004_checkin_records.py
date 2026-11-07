"""Add durable account check-in history."""

from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS checkin_record ("
        "id INTEGER PRIMARY KEY, "
        "account_id INTEGER REFERENCES account(id) ON DELETE SET NULL, "
        "provider VARCHAR(32) NOT NULL, "
        "account_name VARCHAR(128) NOT NULL DEFAULT '', "
        "checked_at DATETIME NOT NULL, "
        "success INTEGER NOT NULL DEFAULT 0, "
        "reward TEXT NOT NULL DEFAULT '', "
        "message TEXT NOT NULL DEFAULT '', "
        "consecutive_days INTEGER, "
        "details TEXT NOT NULL DEFAULT '{}'"
        ")"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_checkin_record_account_id ON checkin_record(account_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_checkin_record_provider ON checkin_record(provider)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_checkin_record_checked_at ON checkin_record(checked_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS checkin_record")
