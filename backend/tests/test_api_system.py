from __future__ import annotations

from p4_helpers import login

from csx.infra.settings import settings


def test_system_backup_endpoints_require_login_and_return_envelopes(client, monkeypatch, tmp_path):
    from csx.api.routes import system

    client.cookies.clear()
    assert client.post("/api/v1/system/backup").status_code == 401
    assert client.get("/api/v1/system/backups").status_code == 401
    login(client)

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    result = client.post("/api/v1/system/backup")
    assert result.status_code == 200
    assert result.json()["ok"] is True
    assert result.json()["data"]["filename"].startswith("csx-backup-")
    assert result.json()["data"]["sha256"]

    listed = client.get("/api/v1/system/backups")
    assert listed.status_code == 200
    assert listed.json()["ok"] is True
    assert listed.json()["data"][0]["filename"] == result.json()["data"]["filename"]
    assert system.router.prefix == "/system"
