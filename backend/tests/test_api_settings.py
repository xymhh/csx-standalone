from p4_helpers import login


class FakeDrive:
    def list_dir(self, path):
        assert path == "/"
        return []


def test_settings_six_sections_grouped_validation_and_test(client):
    login(client)
    sections = ("baseline", "sources", "transfer", "strm", "notify", "advanced")
    for section in sections:
        response = client.put(f"/api/v1/settings/{section}", json={"enabled": True})
        assert response.status_code == 200
        assert response.json()["data"]["enabled"] is True
        assert client.get(f"/api/v1/settings/{section}").json()["data"]["enabled"] is True
    all_config = client.get("/api/v1/settings").json()["data"]
    assert set(all_config) == set(sections)
    assert client.put("/api/v1/settings/unknown", json={}).status_code == 404
    assert client.put("/api/v1/settings/baseline", json={"a.b": 1}).status_code == 422
    provider_test = client.post("/api/v1/settings/test/missing")
    assert provider_test.status_code == 200
    assert provider_test.json()["data"]["valid"] is False
    client.app.state.drives["quark"] = FakeDrive()
    valid_test = client.post("/api/v1/settings/test/quark")
    assert valid_test.json()["data"]["valid"] is True
    client.app.state.drives.pop("quark")
