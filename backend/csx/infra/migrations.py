"""Programmatic Alembic migration entry point."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine


def upgrade_to_head(engine: Engine | None = None) -> None:
    config = Config()
    config.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[2] / "migrations")
    )
    if engine is not None:
        config.attributes["sqlalchemy_url"] = str(engine.url)
    command.upgrade(config, "head")
