from p4_helpers import login
from sqlalchemy import select

from csx.infra.db import SessionLocal
from csx.infra.models import Account
from csx.ports.drive import CloudDirectory


class FakeDrive:
    def list_directories(self, parent_id=""):
        return [CloudDirectory("folder-1", "Movies", "/Movies", True)]

    def create_directory(self, parent_id="", name=""):
        return CloudDirectory("folder-2", name, f"/{name}", False)


def _account_id(client) -> int:
    login(client)
    with SessionLocal() as db:
        account = db.scalar(select(Account).where(Account.provider == "quark"))
        if account is None:
            account = Account(provider="quark", name="browse-test", credential="encrypted")
            db.add(account)
            db.commit()
        return account.id


def test_account_folder_listing_returns_directory_tree_nodes(client, monkeypatch):
    account_id = _account_id(client)
    monkeypatch.setattr("csx.api.routes.drives.drive_for", lambda *_args: FakeDrive())

    response = client.get(f"/api/v1/drives/{account_id}/folders")

    assert response.status_code == 200
    assert response.json()["data"] == [
        {"id": "folder-1", "name": "Movies", "path": "/Movies", "has_children": True}
    ]


def test_account_folder_listing_uses_parent_path_for_nested_nodes(client, monkeypatch):
    account_id = _account_id(client)
    monkeypatch.setattr("csx.api.routes.drives.drive_for", lambda *_args: FakeDrive())

    response = client.get(
        f"/api/v1/drives/{account_id}/folders?parent_id=folder-1&parent_path=Movies"
    )

    assert response.status_code == 200
    assert response.json()["data"][0]["path"] == "/Movies/Movies"


def test_create_folder_returns_created_node(client, monkeypatch):
    account_id = _account_id(client)
    monkeypatch.setattr("csx.api.routes.drives.drive_for", lambda *_args: FakeDrive())

    response = client.post(
        f"/api/v1/drives/{account_id}/folders",
        json={"parent_id": "folder-1", "parent_path": "/Movies", "name": " 新建目录 "},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "id": "folder-2",
        "name": "新建目录",
        "path": "/Movies/新建目录",
        "has_children": False,
    }


def test_create_folder_rejects_invalid_name(client, monkeypatch):
    account_id = _account_id(client)
    monkeypatch.setattr("csx.api.routes.drives.drive_for", lambda *_args: FakeDrive())

    response = client.post(
        f"/api/v1/drives/{account_id}/folders",
        json={"parent_id": "0", "parent_path": "/", "name": "a/b"},
    )

    assert response.status_code == 422
