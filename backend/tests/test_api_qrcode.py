from __future__ import annotations

import base64

import pytest
from p4_helpers import login
from sqlalchemy import delete

from csx.infra.credentials import decrypt_credential
from csx.infra.db import SessionLocal
from csx.infra.models import Account
from csx.infra.settings import settings


def _login(client):
    client.cookies.clear()
    login(client)


def _delete_provider(provider: str) -> None:
    with SessionLocal() as db:
        db.execute(delete(Account).where(Account.provider == provider))
        db.commit()


@pytest.mark.parametrize("provider", ["115", "quark"])
def test_qrcode_start_returns_png_and_provider_token_data(client, monkeypatch, provider):
    _login(client)
    if provider == "115":
        from csx.vendor.drive.p115.client import P115ClientManager

        monkeypatch.setattr(
            P115ClientManager,
            "create_qrcode_login",
            staticmethod(
                lambda client_type: {
                    "uid": "uid-1",
                    "time": "1700000000",
                    "sign": "sign-1",
                    "client_type": client_type,
                    "qrcode": "data:image/png;base64,Zm9v",
                }
            ),
        )
    else:
        from csx.vendor.drive.quark.client import QuarkClient

        monkeypatch.setattr(
            QuarkClient,
            "create_qrcode_login",
            staticmethod(lambda: {"qr_token": "quark-token", "qr_url": "https://qr.test/login"}),
        )

    response = client.post("/api/v1/accounts/qrcode/start", json={"provider": provider})
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["provider"] == provider
    assert payload["qrcode"].startswith("data:image/png;base64,")
    if provider == "115":
        assert payload["token_data"] == {
            "uid": "uid-1",
            "time": "1700000000",
            "sign": "sign-1",
            "client_type": "alipaymini",
        }
    else:
        image = base64.b64decode(payload["qrcode"].split(",", 1)[1])
        assert image.startswith(b"\x89PNG\r\n\x1a\n")
        assert payload["token_data"] == {"qr_token": "quark-token"}


@pytest.mark.parametrize(
    ("vendor_status", "expected"),
    [("waiting", "waiting"), ("scanned", "scanned"), ("expired", "expired")],
)
def test_qrcode_check_normalizes_poll_status(client, monkeypatch, vendor_status, expected):
    _login(client)
    from csx.vendor.drive.p115.client import P115ClientManager

    monkeypatch.setattr(
        P115ClientManager,
        "check_qrcode_login",
        staticmethod(lambda **_kwargs: {"status": vendor_status, "message": "mock status"}),
    )
    response = client.post(
        "/api/v1/accounts/qrcode/check",
        json={"provider": "115", "token_data": {"uid": "u", "time": "t", "sign": "s"}},
    )
    assert response.status_code == 200
    assert response.json()["data"] == {
        "status": expected,
        "message": "mock status",
        "account": None,
    }


def test_qrcode_success_encrypts_cookie_and_auto_saves_account(client, monkeypatch):
    _login(client)
    _delete_provider("115")
    monkeypatch.setattr(settings, "secret_key", "qr-test-secret-key")
    from csx.vendor.drive.p115.client import P115ClientManager

    cookie = "UID=abc; CID=cid-secret; SEID=seid-secret"
    monkeypatch.setattr(
        P115ClientManager,
        "check_qrcode_login",
        staticmethod(lambda **_kwargs: {"status": "success", "message": "done", "cookie": cookie}),
    )
    response = client.post(
        "/api/v1/accounts/qrcode/check",
        json={
            "provider": "115",
            "token_data": {"uid": "u", "time": "t", "sign": "s"},
            "name": "客厅 115",
            "auto_save": True,
        },
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status"] == "success"
    assert body["message"] == "绑定成功"
    assert body["account"]["provider"] == "115"
    assert body["account"]["name"] == "客厅 115"
    assert body["account"]["has_credential"] is True
    assert cookie not in response.text
    with SessionLocal() as db:
        account = db.query(Account).filter_by(provider="115").one()
        assert account.credential != cookie
        assert decrypt_credential(account.credential) == cookie
        account_id = account.id
    client.delete(f"/api/v1/accounts/{account_id}")


def test_qrcode_success_with_auto_save_disabled_never_returns_cookie(client, monkeypatch):
    _login(client)
    _delete_provider("quark")
    from csx.vendor.drive.quark.client import QuarkClient

    cookie = "__pus=secret"
    monkeypatch.setattr(
        QuarkClient,
        "check_qrcode_login",
        staticmethod(lambda **_kwargs: {"status": "success", "cookie": cookie}),
    )
    response = client.post(
        "/api/v1/accounts/qrcode/check",
        json={"provider": "quark", "token_data": {"qr_token": "token"}, "auto_save": False},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "success"
    assert response.json()["data"]["account"] is None
    assert cookie not in response.text
    with SessionLocal() as db:
        assert db.query(Account).filter_by(provider="quark").count() == 0


def test_qrcode_endpoints_require_login(client):
    client.cookies.clear()
    assert client.post("/api/v1/accounts/qrcode/start", json={"provider": "115"}).status_code == 401
    assert (
        client.post(
            "/api/v1/accounts/qrcode/check",
            json={"provider": "115", "token_data": {"uid": "u"}},
        ).status_code
        == 401
    )


def test_qrcode_auto_save_respects_one_account_per_provider(client, monkeypatch):
    _login(client)
    _delete_provider("quark")
    monkeypatch.setattr(settings, "secret_key", "qr-test-secret-key")
    from csx.vendor.drive.quark.client import QuarkClient

    monkeypatch.setattr(
        QuarkClient,
        "check_qrcode_login",
        staticmethod(lambda **_kwargs: {"status": "success", "cookie": "new-cookie"}),
    )
    first = client.post(
        "/api/v1/accounts",
        json={"provider": "quark", "credential": "old-cookie", "name": "原有账号"},
    )
    assert first.status_code == 200
    response = client.post(
        "/api/v1/accounts/qrcode/check",
        json={"provider": "quark", "token_data": {"qr_token": "token"}},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACCOUNT_EXISTS"
    with SessionLocal() as db:
        assert db.query(Account).filter_by(provider="quark").one().name == "原有账号"
    client.delete(f"/api/v1/accounts/{first.json()['data']['id']}")
