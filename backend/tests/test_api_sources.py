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
