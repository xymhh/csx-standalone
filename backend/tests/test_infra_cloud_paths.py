import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from csx.infra.cloud_paths import resolve_cloud_paths
from csx.infra.models import Account, Base, Setting


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_account_paths_win_over_runtime_defaults(db):
    db.add(
        Account(
            provider="p115",
            name="主号",
            credential="x",
            is_primary=True,
            transfer_path="/115/暂存",
            media_path="/115/媒体库",
        )
    )
    db.commit()

    paths = resolve_cloud_paths(db, "p115")

    assert paths["transfer_path"] == "/115/暂存"
    assert paths["media_path"] == "/115/媒体库"
    assert paths["type_folder"] is False


def test_falls_back_to_runtime_defaults_without_account(db):
    paths = resolve_cloud_paths(db, "quark")

    assert paths["transfer_path"] == "/CSX/_inbox"
    assert paths["media_path"] == "/CSX/媒体库"


def test_reads_type_folder_config_from_settings(db):
    db.add_all(
        [
            Setting(key="transfer.type_folder_enabled", value="true"),
            Setting(key="transfer.type_folder_movie", value='"电影"'),
            Setting(key="transfer.type_folder_tv", value='"剧集"'),
        ]
    )
    db.commit()

    paths = resolve_cloud_paths(db, "quark")

    assert paths["type_folder"] is True
    assert paths["type_movie"] == "电影"
    assert paths["type_tv"] == "剧集"


def test_disabled_primary_is_skipped(db):
    db.add_all(
        [
            Account(
                provider="p115",
                name="停用主号",
                credential="x",
                is_primary=True,
                is_enabled=False,
                transfer_path="/停用/暂存",
                media_path="/停用/媒体库",
            ),
            Account(
                provider="p115",
                name="备用号",
                credential="x",
                transfer_path="/备用/暂存",
                media_path="/备用/媒体库",
            ),
        ]
    )
    db.commit()

    paths = resolve_cloud_paths(db, "p115")

    assert paths["transfer_path"] == "/备用/暂存"
