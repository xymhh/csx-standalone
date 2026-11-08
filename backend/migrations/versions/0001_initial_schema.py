"""Create authentication and P1 business tables idempotently."""

from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_TABLES = (
    "CREATE TABLE IF NOT EXISTS admin_user (id INTEGER PRIMARY KEY, username VARCHAR(64) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS auth_session (id INTEGER PRIMARY KEY, token_hash VARCHAR(64) NOT NULL UNIQUE, user_id INTEGER NOT NULL REFERENCES admin_user(id), created_at DATETIME DEFAULT CURRENT_TIMESTAMP, expires_at DATETIME NOT NULL, ip VARCHAR(64) NOT NULL DEFAULT '', user_agent VARCHAR(255) NOT NULL DEFAULT '')",
    "CREATE TABLE IF NOT EXISTS media_item (id INTEGER PRIMARY KEY, tmdb_id INTEGER NOT NULL UNIQUE, type TEXT NOT NULL, title TEXT NOT NULL, year INTEGER, overview TEXT NOT NULL DEFAULT '', poster_url TEXT NOT NULL DEFAULT '', created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS season (id INTEGER PRIMARY KEY, media_id INTEGER NOT NULL REFERENCES media_item(id) ON DELETE CASCADE, season_number INTEGER NOT NULL, episode_count INTEGER NOT NULL DEFAULT 0, UNIQUE(media_id, season_number))",
    "CREATE TABLE IF NOT EXISTS episode (id INTEGER PRIMARY KEY, season_id INTEGER NOT NULL REFERENCES season(id) ON DELETE CASCADE, episode_number INTEGER NOT NULL, air_date DATE, title TEXT NOT NULL DEFAULT '', UNIQUE(season_id, episode_number))",
    "CREATE TABLE IF NOT EXISTS subscription (id INTEGER PRIMARY KEY, media_id INTEGER NOT NULL REFERENCES media_item(id), scope TEXT NOT NULL DEFAULT '{}', quality_pref TEXT NOT NULL DEFAULT '{\"min_bucket\":\"1080p\"}', state TEXT NOT NULL DEFAULT 'active', source TEXT NOT NULL DEFAULT 'manual', created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS discovered_resource (id INTEGER PRIMARY KEY, subscription_id INTEGER NOT NULL REFERENCES subscription(id), provider TEXT NOT NULL, share_url TEXT NOT NULL, dedup_key TEXT NOT NULL UNIQUE, idempotency_key TEXT, score REAL NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'new', payload TEXT NOT NULL DEFAULT '{}', created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS transfer_task (id INTEGER PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE, subscription_id INTEGER REFERENCES subscription(id), resource_id INTEGER REFERENCES discovered_resource(id), state TEXT NOT NULL DEFAULT 'queued', attempt INTEGER NOT NULL DEFAULT 0, next_retry_at DATETIME, dead_letter INTEGER NOT NULL DEFAULT 0, last_error TEXT NOT NULL DEFAULT '', created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS library_file (id INTEGER PRIMARY KEY, episode_id INTEGER NOT NULL REFERENCES episode(id), path TEXT NOT NULL, size INTEGER NOT NULL DEFAULT 0, sha1 TEXT, landed_verified INTEGER NOT NULL DEFAULT 0, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(episode_id, path))",
    "CREATE TABLE IF NOT EXISTS strm_record (id INTEGER PRIMARY KEY, library_file_id INTEGER NOT NULL REFERENCES library_file(id) ON DELETE CASCADE, strm_path TEXT NOT NULL UNIQUE, generated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS account (id INTEGER PRIMARY KEY, provider TEXT NOT NULL, credential TEXT NOT NULL, quota_state TEXT NOT NULL DEFAULT '{}', created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS setting (key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '{}', updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)",
)
_INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_auth_session_token_hash ON auth_session(token_hash)",
    "CREATE INDEX IF NOT EXISTS ix_auth_session_user_id ON auth_session(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_auth_session_expires_at ON auth_session(expires_at)",
    "CREATE INDEX IF NOT EXISTS ix_season_media_id ON season(media_id)",
    "CREATE INDEX IF NOT EXISTS ix_episode_season_id ON episode(season_id)",
    "CREATE INDEX IF NOT EXISTS ix_subscription_media_id ON subscription(media_id)",
    "CREATE INDEX IF NOT EXISTS ix_subscription_state ON subscription(state)",
    "CREATE INDEX IF NOT EXISTS ix_discovered_resource_subscription_id ON discovered_resource(subscription_id)",
    "CREATE INDEX IF NOT EXISTS ix_discovered_resource_state ON discovered_resource(state)",
    "CREATE INDEX IF NOT EXISTS ix_transfer_task_subscription_id ON transfer_task(subscription_id)",
    "CREATE INDEX IF NOT EXISTS ix_transfer_task_resource_id ON transfer_task(resource_id)",
    "CREATE INDEX IF NOT EXISTS ix_transfer_task_state ON transfer_task(state)",
    "CREATE INDEX IF NOT EXISTS ix_transfer_task_next_retry_at ON transfer_task(next_retry_at)",
    "CREATE INDEX IF NOT EXISTS ix_library_file_episode_id ON library_file(episode_id)",
    "CREATE INDEX IF NOT EXISTS ix_strm_record_library_file_id ON strm_record(library_file_id)",
)


def upgrade() -> None:
    for statement in _TABLES + _INDEXES:
        op.execute(statement)


def downgrade() -> None:
    for table in (
        "strm_record",
        "library_file",
        "transfer_task",
        "discovered_resource",
        "subscription",
        "episode",
        "season",
        "media_item",
        "account",
        "setting",
        "auth_session",
        "admin_user",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
