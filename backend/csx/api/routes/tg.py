"""Telegram message parsing, ingestion, and monitor status APIs."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from csx.api.envelope import ok
from csx.application.tg_monitor import ingest_telegram_message, parse_telegram_message
from csx.application.tg_sync import is_configured, load_tg_config, run_scan
from csx.infra.db import SessionLocal, get_db
from csx.infra.events import event_bus
from csx.infra.models import DiscoveredResource, Setting
from csx.infra.tg_client import client_from_config
from csx.infra.tg_errors import TgAuthError, TgNotConfigured
from csx.infra.tg_scan_state import load_state

router = APIRouter(prefix="/tg", tags=["telegram"])


class TelegramParseRequest(BaseModel):
    text: str
    extra_urls: list[str] = Field(default_factory=list)


class TelegramIngestRequest(BaseModel):
    channel: str = Field(min_length=1, max_length=255)
    message_id: int | None = None
    text: str
    auto_transfer: bool | None = None


def _tg_config(db: Session) -> dict[str, Any]:
    row = db.get(Setting, "sources.tgchannels")
    if row is None:
        return {}
    try:
        value = json.loads(row.value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


@router.post("/parse")
def parse_message(body: TelegramParseRequest, db: Session = Depends(get_db)):
    return ok(parse_telegram_message(db, body.text, body.extra_urls))


@router.post("/ingest")
async def ingest_message(body: TelegramIngestRequest, db: Session = Depends(get_db)):
    config = _tg_config(db)
    result = ingest_telegram_message(
        db,
        channel=body.channel,
        message_id=body.message_id,
        text=body.text,
        auto_transfer=(
            body.auto_transfer
            if body.auto_transfer is not None
            else bool(config.get("auto_transfer", True))
        ),
    )
    db.commit()
    for task_id in result["tasks_created"]:
        await event_bus.publish("task_status", {"task_id": task_id, "state": "queued"})
    if result["resources_count"]:
        await event_bus.publish(
            "candidate_found",
            {"source": "telegram", "channel": body.channel, "count": result["resources_count"]},
        )
    return ok(result)


@router.get("/status")
def telegram_status(db: Session = Depends(get_db)):
    config = _tg_config(db)
    channels = config.get("channels", [])
    if isinstance(channels, str):
        channels = [line.strip() for line in channels.splitlines() if line.strip()]
    if not isinstance(channels, list):
        channels = []
    count = (
        db.scalar(
            select(func.count(DiscoveredResource.id)).where(
                DiscoveredResource.payload.contains('"source": "telegram"')
            )
        )
        or 0
    )
    return ok(
        {
            "enabled": bool(config.get("enabled", False)),
            "channels": [str(channel) for channel in channels],
            "auto_transfer": bool(config.get("auto_transfer", True)),
            "ingested_count": int(count),
        }
    )


@router.get("/client/status")
def tg_client_status(request: Request, db: Session = Depends(get_db)):
    config = load_tg_config(db)
    state = load_state(db)
    worker = getattr(request.app.state, "tg_worker", None)
    entries = state.get("channels", {})
    labels = config.get("channel_labels", {})
    channels = []
    for channel in config["channels"]:
        entry = entries.get(channel, {}) if isinstance(entries, dict) else {}
        channels.append(
            {
                "channel": labels.get(channel, channel),
                "last_message_id": int(entry.get("last_message_id") or 0),
                "scanned_at": entry.get("scanned_at"),
                "ingested": int(entry.get("ingested") or 0),
                "error": entry.get("error"),
            }
        )
    return ok(
        {
            "enabled": bool(config["enabled"]),
            "configured": is_configured(config),
            "running": bool(getattr(worker, "running", False)),
            "interval_minutes": int(config["interval_minutes"]),
            "last_scan_at": state.get("last_scan_at"),
            "last_error": state.get("last_error") or getattr(worker, "last_error", None),
            "channels": channels,
        }
    )


@router.post("/client/scan")
async def tg_client_scan():
    try:
        return ok(
            await asyncio.wait_for(
                run_scan(SessionLocal, client_from_config),
                timeout=120,
            )
        )
    except TimeoutError as error:
        raise HTTPException(
            504,
            detail={"code": "TG_SCAN_TIMEOUT", "message": "扫描超时（120 秒），请稍后重试"},
        ) from error
    except TgNotConfigured as error:
        raise HTTPException(
            422,
            detail={"code": "TG_NOT_CONFIGURED", "message": str(error)},
        ) from error
    except TgAuthError as error:
        raise HTTPException(
            422,
            detail={"code": "TG_AUTH_FAILED", "message": str(error)},
        ) from error
