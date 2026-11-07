from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, inspect

from csx.infra.migrations import upgrade_to_head


def test_upgrade_is_repeatable_and_preserves_existing_admin(tmp_path) -> None:
    db_path = tmp_path / "fresh.db"
    engine = create_engine(f"sqlite:///{db_path}")
    expected = {
        "admin_user",
        "auth_session",
        "media_item",
        "season",
        "episode",
        "subscription",
        "discovered_resource",
        "transfer_task",
        "library_file",
        "strm_record",
        "account",
        "setting",
    }
    upgrade_to_head(engine)
    assert expected <= set(inspect(engine).get_table_names())
    upgrade_to_head(engine)
    engine.dispose()

    legacy_path = tmp_path / "legacy.db"
    with sqlite3.connect(legacy_path) as connection:
        connection.execute(
            "CREATE TABLE admin_user (id INTEGER PRIMARY KEY, username VARCHAR(64) NOT NULL UNIQUE, "
            "password_hash VARCHAR(255) NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.execute(
            "INSERT INTO admin_user (username, password_hash) VALUES (?, ?)",
            ("existing", "hash"),
        )
    legacy_engine = create_engine(f"sqlite:///{legacy_path}")
    upgrade_to_head(legacy_engine)
    assert expected <= set(inspect(legacy_engine).get_table_names())
    with sqlite3.connect(legacy_path) as connection:
        assert connection.execute("SELECT username FROM admin_user").fetchone() == ("existing",)
    legacy_engine.dispose()


def test_script_location_points_at_real_migrations_dir() -> None:
    from csx.infra.migrations import script_location

    location = script_location()
    assert (Path(location) / "env.py").is_file()
    assert (Path(location) / "versions" / "0001_initial_schema.py").is_file()
