from p4_helpers import login
from sqlalchemy import select

from csx.infra.db import SessionLocal
from csx.infra.models import Account, ManualTransfer, TransferTask
from csx.ports.drive import ShareFile, ShareStatus


class FakeDrive:
    provider = "quark"

    def check_share(self, share_url, password=""):
        assert share_url == "https://share.example/link"
        assert password == "abcd"
        return ShareStatus(True, share_title="Example share")

    def list_share_files(self, share_url, password=""):
        return [ShareFile("video-1", "Example.S01E01.mkv", 1024, is_dir=False)]


def test_share_inspect_returns_file_tree_metadata(client, monkeypatch):
    login(client)
    with SessionLocal() as db:
        if db.scalar(select(Account).where(Account.provider == "quark")) is None:
            db.add(Account(provider="quark", name="inspect-test", credential="encrypted"))
            db.commit()
    monkeypatch.setattr("csx.api.routes.drives.drive_for", lambda *_args: FakeDrive())

    response = client.post(
        "/api/v1/drives/share/inspect",
        json={"provider": "quark", "share_url": "https://share.example/link", "password": "abcd"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "provider": "quark",
        "share_title": "Example share",
        "files": [{"id": "video-1", "name": "Example.S01E01.mkv", "size": 1024, "is_dir": False}],
        "preview": [],
        "debug": None,
    }


def test_manual_transfer_creates_queued_task_and_persists_selection(client, monkeypatch):
    login(client)
    with SessionLocal() as db:
        account = db.scalar(select(Account).where(Account.provider == "quark"))
        if account is None:
            account = Account(provider="quark", name="manual-test", credential="encrypted")
            db.add(account)
            db.commit()
        account_id = account.id
    monkeypatch.setattr("csx.api.routes.drives.drive_for", lambda *_args: FakeDrive())

    response = client.post(
        "/api/v1/drives/share/transfer",
        json={
            "account_id": account_id,
            "share_url": "https://share.example/link",
            "password": "abcd",
            "file_ids": ["video-1"],
            "target_dir": "/Movies",
        },
    )

    assert response.status_code == 200
    result = response.json()["data"]
    assert result["state"] == "queued"
    with SessionLocal() as db:
        task = db.get(TransferTask, result["task_id"])
        payload = db.get(ManualTransfer, result["task_id"])
        assert task.state == "queued"
        assert task.resource_id is None
        assert payload.target_dir == "/Movies"
        assert payload.file_ids == '["video-1"]'
