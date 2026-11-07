import json
import uuid

from p4_helpers import login

from csx.infra.db import SessionLocal
from csx.infra.models import DiscoveredResource, MediaItem, Subscription, TransferTask


def _subscription(title: str) -> int:
    with SessionLocal() as db:
        media = MediaItem(
            tmdb_id=int(uuid.uuid4().int % 2_000_000_000) + 1,
            type="tv",
            title=title,
        )
        db.add(media)
        db.flush()
        subscription = Subscription(media_id=media.id)
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription.id


def test_telegram_parse_returns_links_episode_and_matching_subscription(client):
    login(client)
    subscription_id = _subscription("测试剧集")
    response = client.post(
        "/api/v1/tg/parse",
        json={
            "text": "《测试剧集》 S01E02 1080p\n夸克：https://pan.quark.cn/s/abc123 提取码: qwer",
            "extra_urls": ["https://115.com/s/xyz789"],
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "测试剧集"
    assert (data["season"], data["episode"]) == (1, 2)
    assert data["matched_subscription_id"] == subscription_id
    assert [(item["provider"], item["password"]) for item in data["links"]] == [
        ("quark", "qwer"),
        ("115", "qwer"),
    ]


def test_telegram_ingest_creates_discovered_resource_and_queued_task(client):
    login(client)
    subscription_id = _subscription("频道测试剧")
    response = client.post(
        "/api/v1/tg/ingest",
        json={
            "channel": "@test_channel",
            "message_id": 42,
            "text": "频道测试剧 S01E03 1080p WEB-DL\nhttps://pan.quark.cn/s/telegram-test 提取码: abcd",
            "auto_transfer": True,
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["ingested"] is True
    assert result["resources_count"] == 1
    assert len(result["tasks_created"]) == 1

    with SessionLocal() as db:
        resource = db.query(DiscoveredResource).filter_by(subscription_id=subscription_id).one()
        payload = json.loads(resource.payload)
        task = db.get(TransferTask, result["tasks_created"][0])
        assert resource.state == "discovered"
        assert resource.provider == "quark"
        assert resource.score > 0
        assert payload["source"] == "telegram"
        assert payload["password"] == "abcd"
        assert payload["season"] == 1 and payload["episode"] == 3
        assert task.state == "queued"

    status = client.get("/api/v1/tg/status")
    assert status.status_code == 200
    assert status.json()["data"]["ingested_count"] >= 1


def test_telegram_ingest_without_auto_transfer_only_creates_candidate(client):
    login(client)
    config_response = client.put(
        "/api/v1/settings/sources",
        json={
            "tgchannels": {"enabled": True, "channels": ["@manual_channel"], "auto_transfer": False}
        },
    )
    assert config_response.status_code == 200
    status = client.get("/api/v1/tg/status").json()["data"]
    assert status["enabled"] is True
    assert status["channels"] == ["@manual_channel"]
    assert status["auto_transfer"] is False
    subscription_id = _subscription("手动确认剧")
    response = client.post(
        "/api/v1/tg/ingest",
        json={
            "channel": "@manual_channel",
            "text": "手动确认剧 S01E01\nhttps://115.com/s/manual-test",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["ingested"] is True
    assert result["tasks_created"] == []
    with SessionLocal() as db:
        assert db.query(DiscoveredResource).filter_by(subscription_id=subscription_id).one()
        assert db.query(TransferTask).filter_by(subscription_id=subscription_id).count() == 0
