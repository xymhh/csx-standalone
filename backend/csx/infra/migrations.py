"""Programmatic Alembic migration entry point."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine


def _candidate_dirs() -> list[Path]:
    """按优先级给出可能存放 migrations/ 的目录。

    线上镜像里 `pip install .` 会把 csx 装进 site-packages，`__file__` 不再是源码树，
    所以不能只靠 parents[2]；按「环境变量 → 源码树 → 当前工作目录 → /app」依次尝试。
    """
    candidates: list[Path] = []
    env_dir = os.environ.get("CSX_MIGRATIONS_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    here = Path(__file__).resolve()
    candidates.extend(
        [
            here.parents[2] / "migrations",
            Path.cwd() / "migrations",
            Path("/app/migrations"),
        ]
    )
    return candidates


def script_location() -> str:
    """定位 alembic 脚本目录，找不到直接抛错（不要静默跑空迁移）。"""
    for candidate in _candidate_dirs():
        if (candidate / "env.py").is_file():
            return str(candidate)
    tried = ", ".join(str(c) for c in _candidate_dirs())
    raise RuntimeError(f"找不到 alembic migrations 目录，已尝试：{tried}")


def upgrade_to_head(engine: Engine | None = None) -> None:
    """把数据库升级到最新版本；幂等，重复调用安全。"""
    config = Config()
    config.set_main_option("script_location", script_location())
    if engine is not None:
        config.attributes["sqlalchemy_url"] = str(engine.url)
    command.upgrade(config, "head")
