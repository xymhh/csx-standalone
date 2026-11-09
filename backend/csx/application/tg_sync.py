"""Orchestration for pulling Telegram channel messages into the CSX ingest flow."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Callable, Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.application.tg_monitor import ingest_telegram_message
from csx.infra.models import Setting
from csx.infra.tg_errors import (
    TgAuthError,
    TgChannelError,
    TgFloodWait,
    TgNotConfigured,
)
from csx.infra.tg_scan_state import load_state, save_state

DEFAULT_INTERVAL_MINUTES = 10
DEFAULT_SCAN_LIMIT = 50
CHANNEL_SLEEP_SECONDS = 1.5

_TG_SETTING_KEYS = (
    "tg_api_id",
    "tg_api_hash",
    "tg_session",
    "tg_channels",
    "tg_monitor_enabled",
    "tg_interval_minutes",
    "tg_auto_transfer",
)


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "off"}
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_advanced(session: Session) -> dict[str, Any]:
    values: dict[str, Any] = {}
    rows = session.scalars(select(Setting).where(Setting.key.like("advanced.%")))
    for row in rows:
        key = row.key.split(".", 1)[1]
        if key not in _TG_SETTING_KEYS:
            continue
        try:
            values[key] = json.loads(row.value)
        except (TypeError, json.JSONDecodeError):
            values[key] = row.value
    return values


def normalize_channel(value: Any) -> str:
    """Normalise common Telegram channel spellings for Telethon."""
    text = str(value or "").strip().strip("'\"").strip()
    if not text:
        return ""
    if text.startswith("@"):
        return text
    if text.startswith("-") or text.isdigit():
        return text
    lowered = text.lower()
    for prefix in ("https://t.me/", "http://t.me/", "https://telegram.me/", "http://telegram.me/"):
        if lowered.startswith(prefix):
            text = text[len(prefix) :]
            break
    else:
        if lowered.startswith("t.me/"):
            text = text[5:]
        elif lowered.startswith("telegram.me/"):
            text = text[12:]
    text = text.split("?", 1)[0].strip("/")
    if not text:
        return ""
    if text.startswith("+") or text.startswith("joinchat"):
        return f"https://t.me/{text}"
    if text.startswith("c/"):
        parts = text.split("/")
        if len(parts) > 1 and parts[1].isdigit():
            return f"-100{parts[1]}"
        return text
    first = text.split("/", 1)[0]
    if not first:
        return ""
    if first.startswith("@"):
        return first
    return f"@{first}"


def _channel_items(raw: Any) -> Iterable[Any]:
    if isinstance(raw, (list, tuple)):
        return raw
    return str(raw or "").splitlines()


def normalize_channels(raw: Any) -> list[str]:
    channels: list[str] = []
    seen: set[str] = set()
    for item in _channel_items(raw):
        channel = normalize_channel(item)
        if not channel or channel in seen:
            continue
        seen.add(channel)
        channels.append(channel)
    return channels


def _channel_labels(raw: Any) -> dict[str, str]:
    labels: dict[str, str] = {}
    for item in _channel_items(raw):
        channel = normalize_channel(item)
        if channel and channel not in labels:
            labels[channel] = str(item or "").strip()
    return labels


def load_tg_config(session: Session) -> dict[str, Any]:
    advanced = _load_advanced(session)
    api_id_text = str(advanced.get("tg_api_id", "") or "").strip()
    api_id = int(api_id_text) if api_id_text.isdigit() and int(api_id_text) > 0 else None
    interval = max(1, _as_int(advanced.get("tg_interval_minutes"), DEFAULT_INTERVAL_MINUTES))
    raw_channels = advanced.get("tg_channels")
    return {
        "enabled": _as_bool(advanced.get("tg_monitor_enabled"), False),
        "api_id": api_id,
        "api_hash": str(advanced.get("tg_api_hash", "") or "").strip(),
        "session": str(advanced.get("tg_session", "") or "").strip(),
        "channels": normalize_channels(raw_channels),
        "channel_labels": _channel_labels(raw_channels),
        "auto_transfer": _as_bool(advanced.get("tg_auto_transfer"), True),
        "interval_minutes": interval,
    }


def is_configured(config: Mapping[str, Any]) -> bool:
    return bool(config.get("api_id") and config.get("api_hash") and config.get("session"))


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _make_client(client_factory: Callable[..., Any], config: Mapping[str, Any]) -> Any:
    try:
        parameters = inspect.signature(client_factory).parameters
    except (TypeError, ValueError):
        parameters = {"config": None}
    if parameters:
        return client_factory(config)
    return client_factory()


async def run_scan(
    session_factory: Callable[[], Any],
    client_factory: Callable[[Mapping[str, Any]], Any],
    *,
    limit: int = DEFAULT_SCAN_LIMIT,
    channel_sleep: float = CHANNEL_SLEEP_SECONDS,
) -> dict[str, Any]:
    """Scan configured channels once and feed every text message into ingest."""
    with session_factory() as session:
        config = load_tg_config(session)
        state = load_state(session)
        summary: dict[str, Any] = {
            "scanned_channels": 0,
            "new_messages": 0,
            "ingested": 0,
            "errors": [],
        }
        if not is_configured(config):
            raise TgNotConfigured("请先配置 Telegram API ID、API Hash 与 StringSession")

        channels: list[str] = list(config["channels"])
        if not channels:
            state["last_scan_at"] = _now_iso()
            state["last_error"] = None
            save_state(session, state)
            session.commit()
            return summary

        client = _make_client(client_factory, config)
        try:
            try:
                await client.connect()
            except TgAuthError as error:
                state["last_error"] = str(error)
                save_state(session, state)
                session.commit()
                raise

            for index, channel in enumerate(channels):
                entry = state["channels"].setdefault(
                    channel,
                    {"last_message_id": 0, "scanned_at": None, "ingested": 0, "error": None},
                )
                min_id = _as_int(entry.get("last_message_id"), 0)
                try:
                    messages = await client.fetch(channel, min_id, limit)
                except TgAuthError as error:
                    state["last_error"] = str(error)
                    save_state(session, state)
                    session.commit()
                    raise
                except TgFloodWait as error:
                    detail = f"{channel}: 触发 Telegram 限流，{error.seconds} 秒后重试"
                    entry["error"] = detail
                    entry["scanned_at"] = _now_iso()
                    summary["errors"].append(detail)
                    save_state(session, state)
                    session.commit()
                    continue
                except TgChannelError as error:
                    detail = f"{channel}: {error}"
                    entry["error"] = detail
                    entry["scanned_at"] = _now_iso()
                    summary["errors"].append(detail)
                    save_state(session, state)
                    session.commit()
                    continue
                except Exception as error:
                    detail = f"{channel}: 扫描失败（{type(error).__name__}）"
                    entry["error"] = detail
                    entry["scanned_at"] = _now_iso()
                    summary["errors"].append(detail)
                    save_state(session, state)
                    session.commit()
                    continue

                ingested_this_channel = 0
                max_id = min_id
                try:
                    for message in sorted(messages, key=lambda item: int(item["id"])):
                        message_id = int(message.get("id") or 0)
                        if message_id <= min_id:
                            continue
                        text = str(message.get("text") or "").strip()
                        max_id = max(max_id, message_id)
                        if not text:
                            continue
                        result = ingest_telegram_message(
                            session,
                            channel=channel,
                            message_id=message_id,
                            text=text,
                            auto_transfer=bool(config["auto_transfer"]),
                        )
                        summary["new_messages"] += 1
                        if result.get("ingested"):
                            ingested_this_channel += 1
                except Exception as error:
                    session.rollback()
                    detail = f"{channel}: 写入候选失败（{type(error).__name__}）"
                    entry["error"] = detail
                    entry["scanned_at"] = _now_iso()
                    summary["errors"].append(detail)
                    save_state(session, state)
                    session.commit()
                    continue

                entry["last_message_id"] = max_id
                entry["scanned_at"] = _now_iso()
                entry["ingested"] = ingested_this_channel
                entry["error"] = None
                summary["scanned_channels"] += 1
                summary["ingested"] += ingested_this_channel
                save_state(session, state)
                session.commit()
                if channel_sleep > 0 and index < len(channels) - 1:
                    await asyncio.sleep(channel_sleep)
        finally:
            await client.close()

        state["last_scan_at"] = _now_iso()
        state["last_error"] = "; ".join(summary["errors"])[:500] if summary["errors"] else None
        save_state(session, state)
        session.commit()
        return summary
