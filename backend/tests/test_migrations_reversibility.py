from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from csx.infra.migrations import script_location


def test_full_migration_chain_repeatedly_upgrades_and_downgrades(tmp_path):
    database = tmp_path / "migration-cycles.db"
    engine = create_engine(f"sqlite:///{database}")
    config = Config()
    config.set_main_option("script_location", script_location())
    config.attributes["sqlalchemy_url"] = str(engine.url)

    for _ in range(2):
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        inspector = inspect(engine)
        assert {"checkin_record", "transfer_task", "library_file"} <= set(
            inspector.get_table_names()
        )
        assert "provider" in {column["name"] for column in inspector.get_columns("library_file")}
        assert "uq_strm_record_library_file_id" in {
            index["name"] for index in inspector.get_indexes("strm_record")
        }

        command.downgrade(config, "0001")
        inspector = inspect(engine)
        assert "checkin_record" not in inspector.get_table_names()
        assert "provider" not in {
            column["name"] for column in inspector.get_columns("library_file")
        }
        assert "uq_strm_record_library_file_id" not in {
            index["name"] for index in inspector.get_indexes("strm_record")
        }

    command.upgrade(config, "head")
    engine.dispose()
