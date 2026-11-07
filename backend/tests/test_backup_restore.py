from __future__ import annotations

import gzip
import hashlib
import sqlite3
import threading
import time

import pytest
from sqlalchemy import create_engine

from csx.infra.backup import create_backup, list_backups, restore_backup


def test_hot_backup_is_consistent_during_active_writes_and_has_checksum(tmp_path):
    database = tmp_path / "live.db"
    engine = create_engine(f"sqlite:///{database}", connect_args={"timeout": 10})
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE item (id INTEGER PRIMARY KEY, value TEXT)")
        connection.exec_driver_sql("INSERT INTO item(value) VALUES ('before')")

    stopping = threading.Event()
    writer_errors = []

    def write_continuously():
        try:
            with sqlite3.connect(database, timeout=10) as connection:
                while not stopping.is_set():
                    connection.execute("INSERT INTO item(value) VALUES ('concurrent')")
                    connection.commit()
        except Exception as error:  # pragma: no cover - failure reported below
            writer_errors.append(error)

    writer = threading.Thread(target=write_continuously)
    writer.start()
    time.sleep(0.02)
    result = create_backup(engine, tmp_path / "backups")
    stopping.set()
    writer.join(timeout=3)

    output = tmp_path / "backups" / result["filename"]
    assert output.name.startswith("csx-backup-") and output.suffixes == [".db", ".gz"]
    assert output.is_file() and not writer.is_alive() and not writer_errors
    assert hashlib.sha256(output.read_bytes()).hexdigest() == result["sha256"]
    assert result["size_bytes"] == output.stat().st_size
    with gzip.open(output, "rb") as compressed:
        snapshot = sqlite3.connect(":memory:")
        snapshot.deserialize(compressed.read())
        assert snapshot.execute("SELECT COUNT(*) FROM item").fetchone()[0] >= 1
        snapshot.close()
    assert result["tables"]["item"] >= 1
    assert list_backups(tmp_path / "backups")[0]["sha256"] == result["sha256"]
    engine.dispose()


def test_restore_validates_and_atomically_replaces_database(tmp_path):
    source_engine = create_engine(f"sqlite:///{tmp_path / 'source.db'}")
    with source_engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE payload (value TEXT NOT NULL)")
        connection.exec_driver_sql("INSERT INTO payload VALUES ('restored value')")
    backup = create_backup(source_engine, tmp_path / "backups")

    target_path = tmp_path / "target.db"
    target_engine = create_engine(f"sqlite:///{target_path}")
    with target_engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE old_data (value TEXT)")
        connection.exec_driver_sql("INSERT INTO old_data VALUES ('preserve emergency')")

    result = restore_backup(target_engine, tmp_path / "backups" / backup["filename"])
    assert result["database"] == str(target_path.resolve())
    with sqlite3.connect(target_path) as connection:
        assert connection.execute("SELECT value FROM payload").fetchone() == ("restored value",)
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name='old_data'"
        ).fetchone() == (0,)
    emergency = tmp_path / "target.db.pre-restore.bak"
    assert emergency.is_file()
    with sqlite3.connect(emergency) as connection:
        assert connection.execute("SELECT value FROM old_data").fetchone() == (
            "preserve emergency",
        )
    source_engine.dispose()


def test_restore_rejects_corrupt_file_without_touching_active_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'active.db'}")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE safe (value TEXT)")
        connection.exec_driver_sql("INSERT INTO safe VALUES ('untouched')")
    corrupt = tmp_path / "corrupt.db.gz"
    with gzip.open(corrupt, "wb") as compressed:
        compressed.write(b"not sqlite")

    with pytest.raises(ValueError, match="SQLite"):
        restore_backup(engine, corrupt)
    with sqlite3.connect(tmp_path / "active.db") as connection:
        assert connection.execute("SELECT value FROM safe").fetchone() == ("untouched",)
    engine.dispose()
