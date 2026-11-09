from p4_helpers import login

from csx.adapters.search.registry import SearchSourceAdapter


def test_source_schema_returns_fifteen_descriptions_and_saved_values(client):
    login(client)
    response = client.get("/api/v1/settings/sources/schema")
    assert response.status_code == 200
    sources = response.json()["data"]
    assert len(sources) == 15
    assert {source["id"] for source in sources} == SearchSourceAdapter.source_ids()
    pansou = next(source for source in sources if source["id"] == "pansou")
    assert pansou["order"] == 5
    fields = [field for group in pansou["groups"] for field in group["fields"]]
    assert {"key", "label", "type", "default", "value", "description"} <= fields[0].keys()
    assert any(field["key"] == "enabled" for field in fields)

    saved = client.put(
        "/api/v1/settings/sources",
        json={"pansou": {"enabled": False, "pansou_url": "https://search.example"}},
    )
    assert saved.status_code == 200
    reread = client.get("/api/v1/settings/sources/schema").json()["data"]
    pansou_after = next(source for source in reread if source["id"] == "pansou")
    pansou_fields = {
        field["key"]: field for group in pansou_after["groups"] for field in group["fields"]
    }
    assert pansou_fields["enabled"]["value"] is False
    assert pansou_fields["pansou_url"]["value"] == "https://search.example"


def test_source_test_endpoint_returns_probe_result_and_isolates_exceptions(client, monkeypatch):
    login(client)
    monkeypatch.setattr(
        SearchSourceAdapter,
        "_probe",
        staticmethod(
            lambda _definition, _config: (_ for _ in ()).throw(RuntimeError("offline fake"))
        ),
    )
    response = client.post("/api/v1/settings/sources/test/pansou")
    assert response.status_code == 200
    assert response.json()["data"]["valid"] is False
    assert response.json()["data"]["elapsed_ms"] >= 0
    assert "offline fake" in response.json()["data"]["message"]

    monkeypatch.setattr(
        SearchSourceAdapter,
        "_probe",
        staticmethod(lambda _definition, _config: (True, "mock connected")),
    )
    success = client.post("/api/v1/settings/sources/test/pansou").json()
    assert success["ok"] is True
    assert success["data"]["valid"] is True
    assert success["data"]["message"] == "mock connected"

    assert client.post("/api/v1/settings/sources/test/not-a-source").status_code == 404


def test_source_endpoints_require_login(client):
    client.cookies.clear()
    assert client.get("/api/v1/settings/sources/schema").status_code == 401
    assert client.put("/api/v1/settings/sources", json={}).status_code == 401
    assert client.post("/api/v1/settings/sources/test/pansou").status_code == 401


def test_source_meta_returns_cached_accounts_and_dynamic_options(client, monkeypatch):
    login(client)
    monkeypatch.setattr(
        SearchSourceAdapter,
        "dynamic_options",
        classmethod(
            lambda cls, scope, key, config: {
                "status": "ok",
                "channels": [{"title": "TG", "value": "tg"}],
                "plugins": [{"title": "pansou", "value": "pansou"}],
            }
        ),
    )
    monkeypatch.setattr(
        SearchSourceAdapter,
        "cached_accounts",
        classmethod(lambda cls: {"hdhive": {"connected": True, "name": "测试用户"}}),
    )
    response = client.get("/api/v1/settings/sources/meta")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["accounts"]["hdhive"]["name"] == "测试用户"
    assert data["options"]["pansou"]["channels"][0]["value"] == "tg"


def test_source_account_refresh_validates_source_and_returns_card(client, monkeypatch):
    login(client)
    assert client.post("/api/v1/settings/sources/account/not-exist").status_code == 404
    monkeypatch.setattr(
        SearchSourceAdapter,
        "account_info",
        classmethod(
            lambda cls, source_id, config, refresh=False: {"connected": True, "name": "阿黄"}
        ),
    )
    response = client.post("/api/v1/settings/sources/account/juying")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "阿黄"


def test_source_options_refresh_reports_unsupported_and_failures(client, monkeypatch):
    login(client)
    assert client.post("/api/v1/settings/sources/options/not-exist/channels").status_code == 404
    monkeypatch.setattr(
        SearchSourceAdapter,
        "dynamic_options",
        classmethod(lambda cls, scope, key, config: (_ for _ in ()).throw(KeyError(scope))),
    )
    assert client.post("/api/v1/settings/sources/options/mikan/channels").status_code == 404
    monkeypatch.setattr(
        SearchSourceAdapter,
        "dynamic_options",
        classmethod(lambda cls, scope, key, config: (_ for _ in ()).throw(RuntimeError("boom"))),
    )
    assert client.post("/api/v1/settings/sources/options/pansou/channels").status_code == 502


def test_hdhive_oauth_start_requires_valid_redirect_uri(client):
    login(client)
    missing = client.post("/api/v1/settings/sources/hdhive/oauth/start", json={})
    assert missing.status_code == 422
    bad_redirect = client.post(
        "/api/v1/settings/sources/hdhive/oauth/start",
        json={"client_id": "abc", "redirect_uri": "ftp://x"},
    )
    assert bad_redirect.status_code == 422
    ok_response = client.post(
        "/api/v1/settings/sources/hdhive/oauth/start",
        json={"client_id": "abc", "redirect_uri": "https://csx.example/oauth/cb"},
    )
    assert ok_response.status_code == 200
    data = ok_response.json()["data"]
    assert "client_id=abc" in data["authorize_url"]
    assert data["state"] and data["expires_in"] == 600


def test_hdhive_oauth_exchange_rejects_unknown_state(client):
    login(client)
    response = client.post(
        "/api/v1/settings/sources/hdhive/oauth/exchange",
        json={
            "client_id": "abc",
            "redirect_uri": "https://csx.example/oauth/cb",
            "app_secret": "secret",
            "callback": "https://csx.example/oauth/cb?code=c&state=missing",
        },
    )
    assert response.status_code == 422
    assert "state" in response.json()["error"]["message"]


def test_global_search_proxy_settings_roundtrip(client):
    login(client)
    assert client.get("/api/v1/settings/sources/global").json()["data"]["search_proxy"] == ""
    bad = client.post("/api/v1/settings/sources/global", json={"search_proxy": "127.0.0.1:7890"})
    assert bad.status_code == 422
    ok_response = client.post(
        "/api/v1/settings/sources/global",
        json={"search_proxy": "socks5h://user:pass@127.0.0.1:1080"},
    )
    assert ok_response.status_code == 200
    saved = client.get("/api/v1/settings/sources/global").json()["data"]["search_proxy"]
    assert saved == "socks5h://user:pass@127.0.0.1:1080"
    assert (
        client.post("/api/v1/settings/sources/global", json={"search_proxy": ""}).status_code == 200
    )
