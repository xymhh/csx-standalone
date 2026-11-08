"""Recreate account table to drop UNIQUE(provider) constraint."""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # 显式使用 SQLite 标准无损重建法移除 UNIQUE(provider)
    bind.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS account_v8 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                credential TEXT NOT NULL,
                is_enabled BOOLEAN NOT NULL DEFAULT 1,
                is_primary BOOLEAN NOT NULL DEFAULT 0,
                quota_state TEXT NOT NULL DEFAULT '{}',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    )
    bind.execute(
        text(
            """
            INSERT INTO account_v8 (id, provider, name, credential, is_enabled, is_primary, quota_state, created_at)
            SELECT id, provider, name, credential, is_enabled, is_primary, quota_state, created_at FROM account;
            """
        )
    )
    bind.execute(text("DROP TABLE account;"))
    bind.execute(text("ALTER TABLE account_v8 RENAME TO account;"))


def downgrade() -> None:
    pass
