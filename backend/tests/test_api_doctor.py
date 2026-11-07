from p4_helpers import login


def test_doctor_reports_database_scheduler_and_disk(client):
    login(client)
    response = client.get("/api/v1/doctor")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["database"]["ok"] is True
    assert {"running", "active_workers", "waiting_queue_depth"} <= set(data["scheduler"])
    assert "writable" in data["disk"]
    assert isinstance(data["accounts"], list)
