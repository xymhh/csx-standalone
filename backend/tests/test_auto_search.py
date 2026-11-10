"""订阅自动搜源：设置、候选落库与自动建任务。"""

from __future__ import annotations

import json
import uuid

from p4_helpers import login

from csx.adapters.search import executor
from csx.infra.db import SessionLocal
from csx.infra.models import DiscoveredResource, MediaItem, TransferTask


def _media(title: str = "自动搜源测试剧", year: int = 2024) -> int:
    with SessionLocal() as db:
        row = MediaItem(
            tmdb_id=int(uuid.uuid4().int % 2_000_000_000) + 1,
            type="tv",
            title=title,
            year=year,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id


def _item(title: str, url: str, *, provider: str = "115", can_transfer: bool = True) -> dict:
    return {
        "title": title,
        "url": url,
        "resource_type": provider,
        "can_transfer": can_transfer,
        "password": "abcd",
        "size_text": "2.1 GB",
        "update_time": "2024-05-01 10:00",
        "source": "pansou",
        "source_name": "PanSou",
    }


def _mock_search(monkeypatch, items):
    def fake(db, keyword, media_type="all", year=None, season=None, source_ids=None, limit=20):
        return {
            "query": keyword,
            "sources": [{"id": "pansou", "name": "PanSou", "status": "ok", "count": len(items)}],
            "items": list(items),
            "total": len(items),
            "elapsed_ms": 3,
        }

    monkeypatch.setattr(executor, "search_resources", fake)


def _subscribe(client, media_id: int, scope: dict | None = None) -> int:
    created = client.post(
        "/api/v1/subscriptions",
        json={
            "media_id": media_id,
            "scope": scope or {"mode": "all"},
            "quality_pref": {"min_bucket": "1080p"},
        },
    )
    assert created.status_code == 200, created.text
    return created.json()["data"]["id"]


def test_auto_search_settings_defaults_and_update(client):
    login(client)
    data = client.get("/api/v1/auto_search/settings").json()["data"]
    assert data["enabled"] is False
    assert data["interval_hours"] == 6
    assert data["auto_transfer"] is True

    saved = client.put(
        "/api/v1/auto_search/settings",
        json={"enabled": True, "interval_hours": 3, "max_per_round": 5},
    ).json()["data"]
    assert saved["enabled"] is True
    assert saved["interval_hours"] == 3
    assert saved["max_per_round"] == 5
    client.put("/api/v1/auto_search/settings", json={"enabled": False})


def test_auto_search_round_skips_when_disabled(client):
    login(client)
    client.put("/api/v1/auto_search/settings", json={"enabled": False})
    data = client.post("/api/v1/auto_search/run", json={"force": False}).json()["data"]
    assert data["result"]["skipped"] == "auto_search_disabled"


def test_auto_search_creates_candidate_and_task(client, monkeypatch):
    login(client)
    media_id = _media()
    sub_id = _subscribe(client, media_id)
    url = f"https://115.com/s/{uuid.uuid4().hex[:10]}?password=abcd"
    _mock_search(monkeypatch, [_item("自动搜源测试剧 S01E03 2024 1080p WEB-DL", url)])

    data = client.post("/api/v1/auto_search/run", json={"subscription_id": sub_id}).json()["data"][
        "result"
    ]
    assert data["ok"] is True
    assert data["candidates"] == 1
    assert len(data["tasks"]) == 1

    with SessionLocal() as db:
        resource = db.query(DiscoveredResource).filter_by(subscription_id=sub_id).one()
        assert resource.state == "accepted"
        payload = json.loads(resource.payload)
        assert payload["season"] == 1
        assert payload["episode"] == 3
        assert payload["quality_bucket"] == "1080p"
        assert payload["whole_season"] is False
        task = db.get(TransferTask, data["tasks"][0])
        assert task is not None
        assert task.resource_id == resource.id

    again = client.post("/api/v1/auto_search/run", json={"subscription_id": sub_id}).json()["data"][
        "result"
    ]
    assert again["candidates"] == 0
    assert again["tasks"] == []
    assert again["skipped"]["duplicate"] >= 1


def test_auto_search_whole_season_goes_to_candidates_only(client, monkeypatch):
    login(client)
    media_id = _media()
    sub_id = _subscribe(client, media_id)
    url = f"https://115.com/s/{uuid.uuid4().hex[:10]}"
    _mock_search(monkeypatch, [_item("自动搜源测试剧 2024 全12集 1080p 合集", url)])

    data = client.post("/api/v1/auto_search/run", json={"subscription_id": sub_id}).json()["data"][
        "result"
    ]
    assert data["candidates"] == 1
    assert data["tasks"] == []
    with SessionLocal() as db:
        resource = db.query(DiscoveredResource).filter_by(subscription_id=sub_id).one()
        assert resource.state == "discovered"
        assert json.loads(resource.payload)["whole_season"] is True


def test_auto_search_filters_low_quality_and_unmatched_title(client, monkeypatch):
    login(client)
    media_id = _media()
    sub_id = _subscribe(client, media_id)
    _mock_search(
        monkeypatch,
        [
            _item("自动搜源测试剧 S01E04 2024 720p", f"https://115.com/s/{uuid.uuid4().hex[:8]}"),
            _item("完全无关的片子 S01E05 2024 1080p", f"https://115.com/s/{uuid.uuid4().hex[:8]}"),
            _item(
                "自动搜源测试剧 S01E06 2024 1080p",
                f"https://115.com/s/{uuid.uuid4().hex[:8]}",
                provider="magnet",
                can_transfer=False,
            ),
        ],
    )
    data = client.post("/api/v1/auto_search/run", json={"subscription_id": sub_id}).json()["data"][
        "result"
    ]
    assert data["candidates"] == 0
    assert data["tasks"] == []
    assert data["skipped"]["quality"] == 1
    assert data["skipped"]["title"] == 1
    assert data["skipped"]["non_share"] == 1
