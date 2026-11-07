from p4_helpers import login, media_row


def test_subscriptions_crud_sync_validation_and_auth(client):
    client.cookies.clear()
    unauthorized = client.get("/api/v1/subscriptions")
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "UNAUTHORIZED"

    login(client)
    media_id = media_row()
    created = client.post(
        "/api/v1/subscriptions",
        json={
            "media_id": media_id,
            "scope": {"mode": "all"},
            "quality_pref": {"min_bucket": "1080p"},
        },
    )
    assert created.status_code == 200
    sub_id = created.json()["data"]["id"]
    assert client.get("/api/v1/subscriptions").json()["data"]
    assert client.get(f"/api/v1/subscriptions/{sub_id}").json()["data"]["media"]["title"]

    patched = client.patch(f"/api/v1/subscriptions/{sub_id}", json={"state": "paused"})
    assert patched.json()["data"]["state"] == "paused"
    synced = client.post(f"/api/v1/subscriptions/{sub_id}/sync")
    assert synced.json()["data"]["triggered"] is True
    assert client.get("/api/v1/candidates?state=discovered").json()["data"]
    assert client.delete(f"/api/v1/subscriptions/{sub_id}").json()["data"]["deleted"] is True

    invalid = client.post("/api/v1/subscriptions", json={"media_id": 0})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    missing = client.post("/api/v1/subscriptions/999999/sync")
    assert missing.status_code == 404
