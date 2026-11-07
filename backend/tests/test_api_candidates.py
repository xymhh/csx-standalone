import json
import uuid

from p4_helpers import login, media_row

from csx.infra.db import SessionLocal
from csx.infra.models import DiscoveredResource, Subscription


def _candidate(subscription_id, share_url):
    with SessionLocal() as db:
        row = DiscoveredResource(
            subscription_id=subscription_id,
            provider="quark",
            share_url=share_url,
            dedup_key=uuid.uuid4().hex,
            state="discovered",
            payload=json.dumps({"season": 1, "episode": 2, "quality_bucket": "1080p"}),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id


def test_candidates_list_accept_ignore_and_errors(client):
    login(client)
    with SessionLocal() as db:
        sub = Subscription(media_id=media_row())
        db.add(sub)
        db.commit()
        db.refresh(sub)
        sub_id = sub.id

    candidate_id = _candidate(sub_id, "https://share.example/test")
    assert client.get(f"/api/v1/candidates?subscription_id={sub_id}").json()["data"]

    accepted = client.post(f"/api/v1/candidates/{candidate_id}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["data"]["state"] == "queued"
    assert client.post(f"/api/v1/candidates/{candidate_id}/ignore").status_code == 409

    ignored = _candidate(sub_id, "share://ignored")
    assert client.post(f"/api/v1/candidates/{ignored}/ignore").json()["data"]["state"] == "ignored"
    assert client.post("/api/v1/candidates/999999/accept").status_code == 404
