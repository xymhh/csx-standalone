from p4_helpers import login
from sqlalchemy import select

from csx.infra.db import SessionLocal
from csx.infra.models import Account
from csx.ports.drive import CloudDirectory


class FakeDrive:
    def list_directories(self, parent_id=""):
        return [CloudDirectory("folder-1", "Movies", "/Movies", True)]


def test_account_folder_listing_returns_directory_tree_nodes(client, monkeypatch):
    login(client)
    with SessionLocal() as db:
        account = db.scalar(select(Account).where(Account.provider == "quark"))
        if account is None:
            account = Account(provider="quark", name="browse-test", credential="encrypted")
            db.add(account)
            db.commit()
        account_id = account.id
    monkeypatch.setattr("csx.api.routes.drives.drive_for", lambda *_args: FakeDrive())

    response = client.get(f"/api/v1/drives/{account_id}/folders")

    assert response.status_code == 200
    assert response.json()["data"] == [
        {"id": "folder-1", "name": "Movies", "path": "/Movies", "has_children": True}
    ]
