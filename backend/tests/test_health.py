from fastapi.testclient import TestClient

from csx.api.main import app

client = TestClient(app)


def test_health_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["status"] == "up"


def test_meta_has_version() -> None:
    resp = client.get("/api/v1/meta")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["name"] == "CloudSubscribeX"
    assert body["data"]["version"]
    assert body["error"] is None
