"""SQLite online backups, validation, and atomic restore helpers."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import Engine

SQLITE_MAGIC = b"SQLite format 3\x00"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _vacuum_into(engine: Engine, destination: Path) -> None:
    if engine.dialect.name != "sqlite":
        raise ValueError("在线备份仅支持 SQLite")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    quoted_path = str(destination.resolve()).replace("'", "''")
    connection = engine.raw_connection()
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(f"VACUUM INTO '{quoted_path}'")
        finally:
            cursor.close()
    finally:
        connection.close()


def _database_stats(path: Path) -> dict[str, int]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        result: dict[str, int] = {}
        for (table_name,) in tables:
            quoted = table_name.replace('"', '""')
            result[table_name] = int(
                connection.execute(f'SELECT COUNT(*) FROM "{quoted}"').fetchone()[0]
            )
        return result
    finally:
        connection.close()


def create_backup(engine: Engine, backup_dir: Path) -> dict:
    """Create a consistent VACUUM snapshot, gzip it, and write its manifest."""
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    output = backup_dir / f"csx-backup-{stamp}.db.gz"
    suffix = 1
    while output.exists():
        output = backup_dir / f"csx-backup-{stamp}-{suffix}.db.gz"
        suffix += 1

    with tempfile.TemporaryDirectory(dir=backup_dir) as temporary_directory:
        snapshot = Path(temporary_directory) / "snapshot.db"
        compressed_temporary = Path(temporary_directory) / "snapshot.db.gz"
        _vacuum_into(engine, snapshot)
        table_counts = _database_stats(snapshot)
        with snapshot.open("rb") as source, gzip.open(compressed_temporary, "wb") as target:
            shutil.copyfileobj(source, target)
        os.replace(compressed_temporary, output)

    payload = {
        "path": str(output),
        "filename": output.name,
        "sha256": _sha256_file(output),
        "size_bytes": output.stat().st_size,
        "created_at": datetime.now(UTC).isoformat(),
        "tables": table_counts,
    }
    manifest = output.with_suffix(output.suffix + ".json")
    temporary_manifest = manifest.with_suffix(manifest.suffix + ".tmp")
    temporary_manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary_manifest, manifest)
    return payload


def list_backups(backup_dir: Path) -> list[dict]:
    """Return backup manifests in descending creation order."""
    result = []
    for backup_file in sorted(Path(backup_dir).glob("csx-backup-*.db.gz"), reverse=True):
        manifest = backup_file.with_suffix(backup_file.suffix + ".json")
        if manifest.is_file():
            try:
                item = json.loads(manifest.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if item.get("filename") == backup_file.name:
                result.append(item)
    return result


def _extract_and_validate(backup_file: Path, destination: Path) -> None:
    try:
        with gzip.open(backup_file, "rb") as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target)
    except (OSError, EOFError) as error:
        raise ValueError("备份文件不是有效 gzip 文件或已损坏") from error
    with destination.open("rb") as database_file:
        if database_file.read(len(SQLITE_MAGIC)) != SQLITE_MAGIC:
            raise ValueError("备份文件不是有效 SQLite 数据库")
    connection = sqlite3.connect(destination)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError(f"SQLite 完整性检查失败：{integrity}")
    except sqlite3.DatabaseError as error:
        raise ValueError("备份文件 SQLite 完整性检查失败") from error
    finally:
        connection.close()


def restore_backup(engine: Engine, backup_file: Path) -> dict:
    """Validate a compressed snapshot, make an emergency snapshot, then replace."""
    backup_file = Path(backup_file).resolve()
    database_path = engine.url.database
    if engine.dialect.name != "sqlite" or not database_path or database_path == ":memory:":
        raise ValueError("安全恢复仅支持文件型 SQLite 数据库")
    target = Path(database_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = backup_file.with_suffix(backup_file.suffix + ".json")
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        actual_hash = _sha256_file(backup_file)
        if actual_hash != manifest.get("sha256"):
            raise ValueError("备份文件 SHA256 校验失败")

    with tempfile.TemporaryDirectory(dir=target.parent) as temporary_directory:
        extracted = Path(temporary_directory) / "restore.db"
        _extract_and_validate(backup_file, extracted)
        emergency = target.with_suffix(target.suffix + ".pre-restore.bak")
        if target.exists():
            _vacuum_into(engine, emergency)
        engine.dispose()
        os.replace(extracted, target)
        Path(f"{target}-wal").unlink(missing_ok=True)
        Path(f"{target}-shm").unlink(missing_ok=True)
    return {
        "restored_from": str(backup_file),
        "database": str(target),
        "emergency_backup": str(emergency) if emergency.exists() else None,
        "tables": _database_stats(target),
    }
