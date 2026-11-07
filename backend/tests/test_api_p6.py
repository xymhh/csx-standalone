import json

from p4_helpers import login, media_row

from csx.infra.db import SessionLocal
from csx.infra.models import CheckinRecord, Episode, LibraryFile, MediaItem, Season, Setting
from csx.infra.settings import settings


def test_checkin_run_and_history_contract(client, monkeypatch):
    client.cookies.clear()
    assert client.post("/api/v1/checkin/run").status_code == 401
    login(client)
    monkeypatch.setattr(settings, "secret_key", "p6-checkin-test-secret")
    created = client.post(
        "/api/v1/accounts",
        json={"provider": "115", "credential": "cookie", "name": "Checkin Test"},
    )
    assert created.status_code == 200
    account_id = created.json()["data"]["id"]

    from csx.adapters.drive.registry import DriveRegistry

    monkeypatch.setattr(
        DriveRegistry,
        "checkin",
        staticmethod(
            lambda provider, credential, config: {
                "success": True,
                "signin_points": 12,
                "signin_days": 3,
                "message": "签到成功",
            }
        ),
    )
    response = client.post("/api/v1/checkin/run", json={"account_id": account_id})
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["data"]["succeeded"] == 1
    history = client.get(f"/api/v1/checkin/history?account_id={account_id}")
    assert history.status_code == 200
    record = history.json()["data"][0]
    assert record["success"] and record["reward"] == "12"
    assert record["consecutive_days"] == 3
    with SessionLocal() as db:
        assert db.query(CheckinRecord).filter_by(account_id=account_id).count() == 1
    client.delete(f"/api/v1/accounts/{account_id}")


def test_strm_sync_records_and_envelope(client, tmp_path):
    client.cookies.clear()
    login(client)
    with SessionLocal() as db:
        media_id = media_row()
        media = db.get(MediaItem, media_id)
        season = Season(media_id=media.id, season_number=1)
        db.add(season)
        db.flush()
        episode = Episode(season_id=season.id, episode_number=1)
        db.add(episode)
        db.flush()
        library = LibraryFile(
            episode_id=episode.id,
            path="Show/Season 01/Show S01E01.mkv",
            size=100,
            quality_bucket="hd",
            provider="115",
        )
        db.add(library)
        db.add_all(
            [
                Setting(key="strm.strm_root", value=json.dumps(str(tmp_path))),
                Setting(key="strm.mode", value=json.dumps("local_mount")),
                Setting(key="strm.local_mount_root", value=json.dumps("/mnt/cloud")),
            ]
        )
        db.commit()
        library_id = library.id

    response = client.post("/api/v1/strm/sync", json={"library_file_id": library_id})
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["data"]["generated"] == 1
    records = client.get(f"/api/v1/strm/records?library_file_id={library_id}")
    assert records.status_code == 200
    assert len(records.json()["data"]) == 1
    assert (
        tmp_path / "Show/Season 01/Show S01E01.strm"
    ).read_text() == "/mnt/cloud/Show/Season 01/Show S01E01.mkv\n"
    with SessionLocal() as db:
        db.query(Setting).filter(Setting.key.like("strm.%")).delete(synchronize_session=False)
        db.commit()


def test_strm_sync_requires_configuration_and_routes_authenticate(client):
    client.cookies.clear()
    assert client.get("/api/v1/strm/records").status_code == 401
    login(client)
    response = client.post("/api/v1/strm/sync", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_STRM_CONFIG"


def test_library_servers_returns_live_probe_state(client, monkeypatch):
    client.cookies.clear()
    login(client)

    class FakeServer:
        provider = "emby"

        def probe(self):
            from csx.adapters.media.emby import ServerInfo

            return ServerInfo("emby", "Media Home", "4.8", {})

        def close(self):
            pass

    from csx.api.routes import resources

    monkeypatch.setattr(resources, "server_clients", lambda _config: [FakeServer()])
    response = client.get("/api/v1/library/servers")
    assert response.status_code == 200 and response.json()["ok"] is True
    states = {item["provider"]: item for item in response.json()["data"]}
    assert states["emby"]["valid"] is True
    assert states["emby"]["name"] == "Media Home"
    assert states["jellyfin"]["configured"] is False


def test_p6_schema_migrations_include_checkin_and_strm_provider():
    from sqlalchemy import inspect

    from csx.infra.db import engine

    inspector = inspect(engine)
    assert "checkin_record" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("library_file")}
    assert "provider" in columns
