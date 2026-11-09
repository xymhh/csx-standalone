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


def test_doctor_skips_network_probe_by_default(client):
    login(client)
    from csx.infra.db import SessionLocal
    from csx.infra.models import Account

    with SessionLocal() as db:
        db.add(Account(provider="115", credential="enc:test", is_enabled=True))
        db.commit()

    response = client.get("/api/v1/doctor")
    assert response.status_code == 200
    accounts = response.json()["data"]["accounts"]
    assert accounts
    assert all(item["valid"] is None for item in accounts)
    assert all(item["message"] == "" for item in accounts)
