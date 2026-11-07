from p4_helpers import login

from csx.infra.db import SessionLocal
from csx.infra.models import Account
from csx.infra.settings import settings


class FakeDrive:
    def list_dir(self, path):
        assert path == "/"
        return []


def test_account_crud_encrypts_credentials_and_masks_responses(client, monkeypatch):
    login(client)
    monkeypatch.setattr(settings, "secret_key", "P4-test-secret-key")
    client.app.state.drives["quark"] = FakeDrive()
    secret = "cookie-private-value"
    created = client.post(
        "/api/v1/accounts", json={"provider": "quark", "credential": secret, "name": "Home"}
    )
    assert created.status_code == 200
    payload = created.json()["data"]
    account_id = payload["id"]
    assert payload["has_credential"] is True
    assert payload["masked"] == "***"
    assert secret not in created.text

    with SessionLocal() as db:
        stored = db.get(Account, account_id).credential
        assert stored != secret
        assert secret not in stored

    listed = client.get("/api/v1/accounts").json()["data"]
    assert next(item for item in listed if item["id"] == account_id)["masked"] == "***"
    assert client.post(f"/api/v1/accounts/{account_id}/test").json()["data"]["valid"] is True
    updated = client.patch(
        f"/api/v1/accounts/{account_id}", json={"credential": "replacement-secret", "name": "New"}
    )
    assert updated.json()["data"]["name"] == "New"
    assert "replacement-secret" not in updated.text
    assert client.delete(f"/api/v1/accounts/{account_id}").json()["data"]["deleted"] is True
    assert client.post("/api/v1/accounts/999999/test").status_code == 404


def test_account_validation_and_auth(client):
    client.cookies.clear()
    assert client.get("/api/v1/accounts").status_code == 401
    from p4_helpers import login

    login(client)
    invalid = client.post(
        "/api/v1/accounts", json={"provider": "unsupported", "credential": "x", "name": "x"}
    )
    assert invalid.status_code == 422


def test_account_creation_requires_configured_encryption_key(client, monkeypatch):
    from p4_helpers import login

    login(client)
    monkeypatch.setattr(settings, "secret_key", "")
    response = client.post(
        "/api/v1/accounts", json={"provider": "115", "credential": "cookie", "name": "Test"}
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SECRET_KEY_REQUIRED"
