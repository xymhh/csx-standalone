from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import pytest
from p4_helpers import login
from sqlalchemy import select

from csx.api.routes import tg as tg_routes
from csx.application.tg_sync import normalize_channel, run_scan
from csx.infra.bootstrap import init_db
from csx.infra.db import SessionLocal
from csx.infra.models import (
    DiscoveredResource,
    MediaItem,
    Setting,
    Subscription,
    TransferTask,
)
from csx.infra.tg_errors import TgAuthError, TgChannelError, TgFloodWait, TgNotConfigured
from csx.infra.tg_scan_state import SCAN_STATE_KEY, load_state


class FakeClient:
    def __init__(
        self,
        *,
        messages: list[dict[str, Any]] | dict[str, list[dict[str, Any]]] | None = None,
        errors: dict[str, Exception] | None = None,
        connect_error: Exception | None = None,
    ) -> None:
        self.messages = messages or []
        self.errors = errors or {}
        self.connect_error = connect_error
        self.calls: list[tuple[str, int, int]] = []
        self.connected = False
        self.closed = False

    async def connect(self) -> None:
        if self.connect_error is not None:
            raise self.connect_error
        self.connected = True

    async def close(self) -> None:
        self.closed = True

    async def fetch(self, channel: str, min_id: int, limit: int) -> list[dict[str, Any]]:
        self.calls.append((channel, min_id, limit))
        error = self.errors.get(channel)
        if error is not None:
            raise error
        source = (
            self.messages.get(channel, []) if isinstance(self.messages, dict) else self.messages
        )
        return [item for item in source if int(item["id"]) > min_id][:limit]


def _clear_tg_settings() -> None:
    with SessionLocal() as db:
        for row in db.scalars(select(Setting).where(Setting.key.like("advanced.%"))):
            if row.key.startswith("advanced.tg_"):
                db.delete(row)
        state = db.get(Setting, SCAN_STATE_KEY)
        if state is not None:
            db.delete(state)
        db.commit()


def _configure(**overrides: Any) -> None:
    values: dict[str, Any] = {
        "tg_monitor_enabled": False,
        "tg_channels": "@TestChannel",
        "tg_api_id": "12345",
        "tg_api_hash": "0123456789abcdef0123456789abcdef",
        "tg_session": "fake-string-session",
        "tg_auto_transfer": True,
        "tg_interval_minutes": 10,
    }
    values.update(overrides)
    with SessionLocal() as db:
        for key, value in values.items():
            row = db.get(Setting, f"advanced.{key}")
            if row is None:
                db.add(Setting(key=f"advanced.{key}", value=json.dumps(value, ensure_ascii=False)))
            else:
                row.value = json.dumps(value, ensure_ascii=False)
        db.commit()


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


@pytest.fixture(scope="module", autouse=True)
def _ensure_db():
    init_db()


@pytest.fixture(autouse=True)
def _isolated_tg_settings():
    _clear_tg_settings()
    yield
    _clear_tg_settings()


def test_scan_raises_when_not_configured() -> None:
    _configure(tg_api_id="", tg_api_hash="", tg_session="")
    created: list[Any] = []

    with pytest.raises(TgNotConfigured):
        asyncio.run(
            run_scan(
                SessionLocal,
                lambda config: created.append(config) or FakeClient(),
                channel_sleep=0,
            )
        )

    assert created == []


def test_client_status_and_scan_report_unconfigured(client) -> None:
    login(client)
    status = client.get("/api/v1/tg/client/status")
    assert status.status_code == 200
    data = status.json()["data"]
    assert data["configured"] is False
    assert data["enabled"] is False
    assert data["channels"] == []

    response = client.post("/api/v1/tg/client/scan")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TG_NOT_CONFIGURED"


def test_auth_failure_is_recorded_and_mapped_to_422(client, monkeypatch) -> None:
    _configure()
    with pytest.raises(TgAuthError):
        asyncio.run(
            run_scan(
                SessionLocal,
                lambda _config: FakeClient(connect_error=TgAuthError("会话失效")),
                channel_sleep=0,
            )
        )
    with SessionLocal() as db:
        state = load_state(db)
    assert "会话失效" in str(state["last_error"])

    login(client)
    monkeypatch.setattr(
        tg_routes,
        "client_from_config",
        lambda _config: FakeClient(connect_error=TgAuthError("会话失效")),
    )
    response = client.post("/api/v1/tg/client/scan")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TG_AUTH_FAILED"


def test_flood_wait_does_not_advance_channel_cursor() -> None:
    _configure(tg_channels="@FloodChannel")
    fake = FakeClient(errors={"@FloodChannel": TgFloodWait(45)})

    result = asyncio.run(run_scan(SessionLocal, lambda _config: fake, channel_sleep=0))

    assert result["scanned_channels"] == 0
    assert result["ingested"] == 0
    assert any("45" in error for error in result["errors"])
    with SessionLocal() as db:
        state = load_state(db)
    entry = state["channels"]["@FloodChannel"]
    assert entry["last_message_id"] == 0
    assert "限流" in entry["error"]


def test_cursor_advances_and_second_scan_is_incremental() -> None:
    _configure(tg_channels="https://t.me/CursorChannel")
    fake = FakeClient(
        messages=[
            {"id": 100, "text": "旧消息", "date": None},
            {"id": 101, "text": "新消息", "date": None},
        ]
    )

    first = asyncio.run(run_scan(SessionLocal, lambda _config: fake, channel_sleep=0))
    second = asyncio.run(run_scan(SessionLocal, lambda _config: fake, channel_sleep=0))

    assert first["new_messages"] == 2
    assert second["new_messages"] == 0
    assert [call[1] for call in fake.calls] == [0, 101]
    with SessionLocal() as db:
        state = load_state(db)
    assert state["channels"]["@CursorChannel"]["last_message_id"] == 101


def test_one_bad_channel_does_not_block_other_channels() -> None:
    _configure(tg_channels="@GoodChannel\nhttps://t.me/BadChannel")
    fake = FakeClient(
        messages={"@GoodChannel": [{"id": 10, "text": "正常消息", "date": None}]},
        errors={"@BadChannel": TgChannelError("频道不可访问")},
    )

    result = asyncio.run(run_scan(SessionLocal, lambda _config: fake, channel_sleep=0))

    assert result["scanned_channels"] == 1
    assert result["new_messages"] == 1
    assert len(result["errors"]) == 1
    with SessionLocal() as db:
        state = load_state(db)
        good = state["channels"]["@GoodChannel"]
        bad = state["channels"]["@BadChannel"]
    assert good["last_message_id"] == 10
    assert good["error"] is None
    assert "频道不可访问" in bad["error"]


def test_scan_feeds_messages_into_existing_ingest_pipeline() -> None:
    subscription_id = _subscription("TG 编排测试剧")
    _configure(tg_channels="@IngestChannel")
    fake = FakeClient(
        messages=[
            {
                "id": 7,
                "text": (
                    "《TG 编排测试剧》 S01E02 1080p WEB-DL\n"
                    "https://pan.quark.cn/s/tg-scan-orchestration 提取码: abcd"
                ),
                "date": None,
            }
        ]
    )

    result = asyncio.run(run_scan(SessionLocal, lambda _config: fake, channel_sleep=0))

    assert result["new_messages"] == 1
    assert result["ingested"] == 1
    with SessionLocal() as db:
        resource = db.query(DiscoveredResource).filter_by(subscription_id=subscription_id).one()
        payload = json.loads(resource.payload)
        task = db.query(TransferTask).filter_by(subscription_id=subscription_id).one()
    assert payload["source"] == "telegram"
    assert payload["channel"] == "@IngestChannel"
    assert payload["message_id"] == 7
    assert task.state == "queued"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://t.me/QukanMovie", "@QukanMovie"),
        ("t.me/QukanMovie", "@QukanMovie"),
        ("@QukanMovie", "@QukanMovie"),
        ("QukanMovie", "@QukanMovie"),
        ("https://t.me/+abcdef", "https://t.me/+abcdef"),
    ],
)
def test_normalize_channel(raw: str, expected: str) -> None:
    assert normalize_channel(raw) == expected


def test_client_status_returns_configured_channels(client) -> None:
    _configure(tg_channels="https://t.me/StatusChannel", tg_monitor_enabled=True)
    login(client)

    response = client.get("/api/v1/tg/client/status")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["configured"] is True
    assert data["enabled"] is True
    assert data["interval_minutes"] == 10
    assert data["channels"][0]["channel"] == "https://t.me/StatusChannel"
    assert data["channels"][0]["last_message_id"] == 0
