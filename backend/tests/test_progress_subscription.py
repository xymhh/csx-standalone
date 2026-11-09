from p4_helpers import login, media_row

from csx.infra.db import SessionLocal
from csx.infra.models import Subscription


def _add_subscription(media_id: int, state: str) -> int:
    with SessionLocal() as db:
        row = Subscription(media_id=media_id, state=state)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id


def _progress_item(client, media_id: int) -> dict:
    overview = client.get("/api/v1/progress").json()["data"]
    return next(item for item in overview if item["media_id"] == media_id)


def test_progress_returns_active_subscription(client):
    login(client)
    media_id = media_row()
    subscription_id = _add_subscription(media_id, "active")

    item = _progress_item(client, media_id)
    assert item["subscription_id"] == subscription_id
    assert item["subscription_state"] == "active"

    single = client.get(f"/api/v1/progress/{media_id}").json()["data"]
    assert single["subscription_id"] == subscription_id
    assert single["subscription_state"] == "active"


def test_progress_prefers_active_over_paused_regardless_of_order(client):
    login(client)
    paused_first_media = media_row()
    _add_subscription(paused_first_media, "paused")
    paused_first_active = _add_subscription(paused_first_media, "active")

    active_first_media = media_row()
    active_first_active = _add_subscription(active_first_media, "active")
    _add_subscription(active_first_media, "paused")

    first = _progress_item(client, paused_first_media)
    assert first["subscription_id"] == paused_first_active
    assert first["subscription_state"] == "active"

    second = _progress_item(client, active_first_media)
    assert second["subscription_id"] == active_first_active
    assert second["subscription_state"] == "active"


def test_progress_ignores_deleted_subscription(client):
    login(client)
    media_id = media_row()
    subscription_id = _add_subscription(media_id, "active")
    assert client.delete(f"/api/v1/subscriptions/{subscription_id}").status_code == 200

    item = _progress_item(client, media_id)
    assert item["subscription_id"] is None
    assert item["subscription_state"] is None


def test_progress_without_subscription_returns_null(client):
    login(client)
    media_id = media_row()

    item = _progress_item(client, media_id)
    assert item["subscription_id"] is None
    assert item["subscription_state"] is None
