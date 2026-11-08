"""解析「当前生效」的网盘路径与媒体分层配置。

优先级（2026-11-09 确立）：
1. 网盘账号卡片上的「转存暂存路径 / 媒体库归档路径」（账号级，支持同平台多账号各自独立）；
2. 该账号未填时回退到运行时 `CSX_TRANSFER_ROOT` / `CSX_LIBRARY_ROOT`；
3. 都没有则用 `/CSX/_inbox` 与 `/CSX/媒体库`。

「按媒体类型分层」开关与目录名存在 `transfer.*` 配置分组里。
"""

from __future__ import annotations

import json
import posixpath

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.infra.models import Account, Setting
from csx.infra.settings import settings as runtime_settings

DEFAULT_TRANSFER_PATH = "/CSX/_inbox"
DEFAULT_MEDIA_PATH = "/CSX/媒体库"
DEFAULT_TYPE_MOVIE = "电影"
DEFAULT_TYPE_TV = "电视剧"


def normalize_path(value: object, fallback: str) -> str:
    """统一成以 / 开头、无尾斜杠的 posix 路径。"""
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return fallback
    if not text.startswith("/"):
        text = "/" + text
    return text.rstrip("/") or "/"


def _section(db: Session, name: str) -> dict:
    values: dict = {}
    for row in db.scalars(select(Setting).where(Setting.key.like(f"{name}.%"))):
        key = row.key.split(".", 1)[1]
        try:
            values[key] = json.loads(row.value)
        except (TypeError, ValueError):
            continue
    return values


def pick_account(db: Session, provider: str, account_id: int | None = None) -> Account | None:
    """指定账号优先，否则取该平台已启用的主号，再退回最早创建的已启用账号。"""
    if account_id:
        account = db.get(Account, int(account_id))
        if account is not None:
            return account
    provider = str(provider or "").lower()
    if not provider:
        return None
    base = select(Account).where(Account.provider == provider)
    account = db.scalar(base.where(Account.is_primary.is_(True), Account.is_enabled.is_(True)))
    if account is not None:
        return account
    return db.scalar(base.where(Account.is_enabled.is_(True)).order_by(Account.id))


def resolve_cloud_paths(db: Session, provider: str, account_id: int | None = None) -> dict:
    """返回本次任务应使用的转存/归档路径与分层配置。"""
    account = pick_account(db, provider, account_id)
    config = _section(db, "transfer")
    transfer_default = normalize_path(
        posixpath.join(str(runtime_settings.transfer_root or "CSX"), "_inbox"),
        DEFAULT_TRANSFER_PATH,
    )
    media_default = normalize_path(runtime_settings.library_root, DEFAULT_MEDIA_PATH)
    movie = str(config.get("type_folder_movie") or DEFAULT_TYPE_MOVIE).strip() or DEFAULT_TYPE_MOVIE
    tv = str(config.get("type_folder_tv") or DEFAULT_TYPE_TV).strip() or DEFAULT_TYPE_TV
    return {
        "account": account,
        "transfer_path": normalize_path(getattr(account, "transfer_path", ""), transfer_default),
        "media_path": normalize_path(getattr(account, "media_path", ""), media_default),
        "type_folder": bool(config.get("type_folder_enabled", False)),
        "type_movie": movie.strip("/"),
        "type_tv": tv.strip("/"),
    }
