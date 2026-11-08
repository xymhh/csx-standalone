"""Add account is_enabled and is_primary, relax unique constraint."""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 彻底重建 account 表，彻底移除 UNIQUE(provider)
    bind = op.get_bind()
    bind.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS account_new (
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
            INSERT INTO account_new (id, provider, name, credential, is_enabled, is_primary, quota_state, created_at)
            SELECT id, provider, name, credential, 1, 0, quota_state, created_at FROM account;
            """
        )
    )
    bind.execute(text("DROP TABLE account;"))
    bind.execute(text("ALTER TABLE account_new RENAME TO account;"))


def downgrade() -> None:
    pass
