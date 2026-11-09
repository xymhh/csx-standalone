"""跨盘转存设置与库盘解析。

中继执行在 ``csx/adapters/drive/cross_relay.py``；本模块只负责配置读写、
媒体库盘解析与缓存目录选择，不直接接触 vendor。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.adapters.drive.vendor_providers import (
    SUPPORTED_PROVIDERS,
    build_all,
    enabled_accounts,
)
from csx.infra.models import Account, Setting

logger = logging.getLogger(__name__)

SETTING_KEY = "transfer.cross"
DEFAULT_CACHE_DIR = "/cache"
FALLBACK_CACHE_DIR = "/tmp/csx-cache"

DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "library_drive": "",
    "download_threads": 5,
    "max_concurrent": 2,
    "direct_stream": True,
    "cache_dir": DEFAULT_CACHE_DIR,
}

__all__ = [
    "DEFAULTS",
    "DEFAULT_CACHE_DIR",
    "SUPPORTED_PROVIDERS",
    "build_cross_service",
    "enabled_accounts",
    "load_cross_settings",
    "resolve_cache_dir",
    "resolve_library_drive",
    "save_cross_settings",
]


def _coerce(raw: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULTS)
    merged.update({key: raw[key] for key in DEFAULTS if key in raw})
    try:
        merged["download_threads"] = max(1, min(int(merged["download_threads"] or 5), 16))
    except (TypeError, ValueError):
        merged["download_threads"] = DEFAULTS["download_threads"]
    try:
        merged["max_concurrent"] = max(1, min(int(merged["max_concurrent"] or 2), 4))
    except (TypeError, ValueError):
        merged["max_concurrent"] = DEFAULTS["max_concurrent"]
    merged["enabled"] = bool(merged["enabled"])
    merged["direct_stream"] = bool(merged["direct_stream"])
    merged["library_drive"] = str(merged["library_drive"] or "").strip().lower()
    merged["cache_dir"] = str(merged["cache_dir"] or DEFAULT_CACHE_DIR).strip() or DEFAULT_CACHE_DIR
    return merged


def load_cross_settings(db: Session) -> dict[str, Any]:
    """读取跨盘设置；未保存过时返回默认值。"""
    row = db.get(Setting, SETTING_KEY)
    data: dict[str, Any] = {}
    if row is not None:
        try:
            parsed = json.loads(row.value)
            if isinstance(parsed, dict):
                data = parsed
        except (TypeError, json.JSONDecodeError):
            logger.warning("跨盘设置不是合法 JSON，使用默认值")
    return _coerce(data)


def save_cross_settings(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    merged = _coerce({**load_cross_settings(db), **(payload or {})})
    row = db.get(Setting, SETTING_KEY)
    value = json.dumps(merged, ensure_ascii=False)
    if row is None:
        db.add(Setting(key=SETTING_KEY, value=value))
    else:
        row.value = value
    db.commit()
    return merged


def resolve_library_drive(db: Session, cfg: dict[str, Any] | None = None) -> str:
    """媒体库盘：显式设置 → is_primary 账号 → 115。"""
    config = cfg or load_cross_settings(db)
    explicit = str(config.get("library_drive") or "").strip().lower()
    if explicit:
        return explicit
    primary = db.scalars(
        select(Account)
        .where(Account.is_enabled.is_(True), Account.is_primary.is_(True))
        .order_by(Account.id.asc())
    ).first()
    if primary is not None and str(primary.provider or "").lower() in SUPPORTED_PROVIDERS:
        return str(primary.provider).lower()
    accounts = enabled_accounts(db)
    if "115" in accounts:
        return "115"
    return next(iter(accounts), "")


def resolve_cache_dir(cfg: dict[str, Any] | None = None) -> Path:
    """缓存目录：优先配置值，不可写时回退 /tmp/csx-cache。"""
    config = cfg or DEFAULTS
    for candidate in (
        str(config.get("cache_dir") or DEFAULT_CACHE_DIR),
        FALLBACK_CACHE_DIR,
    ):
        path = Path(candidate)
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".csx-write-probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return path
        except OSError as error:
            logger.warning(f"跨盘缓存目录不可用 {path}：{error}")
    return Path(FALLBACK_CACHE_DIR)


def build_cross_service(db: Session, cfg: dict[str, Any] | None = None, on_change=None):
    """按需构造跨盘中继；源盘或目标盘没账号时抛错，由调用方决定重试语义。"""
    from csx.adapters.drive.cross_relay import CrossRelay

    config = cfg or load_cross_settings(db)
    providers = build_all(db)
    return CrossRelay(
        providers,
        cache_dir=str(resolve_cache_dir(config)),
        download_threads=int(config.get("download_threads") or 5),
        max_concurrent=int(config.get("max_concurrent") or 2),
        direct_stream=bool(config.get("direct_stream", True)),
        on_change=on_change,
    )
