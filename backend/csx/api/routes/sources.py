"""Dynamic search-source configuration endpoints.

All routes are mounted beneath ``/api/v1`` and protected by ``auth_guard`` in
``csx.api.main`` before they can read or modify persisted source settings.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.adapters.search.registry import SearchSourceAdapter
from csx.api.envelope import ok
from csx.infra.db import get_db
from csx.infra.models import Setting

router = APIRouter(prefix="/settings/sources", tags=["settings"])


def _saved_sources(db: Session) -> dict[str, Any]:
    rows = db.scalars(select(Setting).where(Setting.key.like("sources.%"))).all()
    saved: dict[str, Any] = {}
    for row in rows:
        key = row.key.removeprefix("sources.")
        try:
            saved[key] = json.loads(row.value)
        except (TypeError, json.JSONDecodeError):
            saved[key] = row.value
    return saved


def _vendor_config(saved: dict[str, Any]) -> dict[str, Any]:
    """合并「定义默认值 ← 已保存值」，让测试/选项探测在未保存时也有可用默认。"""
    config: dict[str, Any] = {}
    for definition in SearchSourceAdapter.definitions():
        for group in definition.get_config_groups():
            for spec in group.fields:
                if spec.key and spec.default not in (None, "", [], {}):
                    config.setdefault(spec.key, spec.default)
    for source_values in saved.values():
        if isinstance(source_values, dict):
            config.update(source_values)
    return config


_PROXY_RE = re.compile(r"^(https?|socks5h?)://[^\s]+$", re.IGNORECASE)


def _upsert_setting(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=value))
    else:
        row.value = value
        row.updated_at = datetime.now(UTC)
    db.commit()


_MAGNET_DEFAULT = "https://itorrents.org/torrent/{info_hash}.torrent"
_RESOURCE_ORDER_DEFAULT = ["115", "ed2k"]
_RESOURCE_LABELS = {
    "115": "115网盘",
    "quark": "quark",
    "123": "123网盘",
    "alipan": "阿里云盘",
    "guangya": "光雅",
    "tianyi": "天翼云盘",
    "yun139": "移动云盘",
    "ed2k": "ed2k",
    "magnet": "magnet",
}


def _searchable_source_options() -> list[dict[str, str]]:
    """可参与搜索的渠道清单（频道监控这类非查询渠道不参与排序）。"""
    options: list[dict[str, str]] = []
    for schema in SearchSourceAdapter.schemas():
        source_id = str(schema.get("id") or "")
        if not source_id or source_id == "tgchannels":
            continue
        options.append({"id": source_id, "name": str(schema.get("name") or source_id)})
    return options


def _resource_options() -> list[dict[str, str]]:
    return [{"id": key, "name": label} for key, label in _RESOURCE_LABELS.items()]


def _clean_order(values: Any, allowed: set[str]) -> list[str]:
    if isinstance(values, str):
        values = [part for part in values.split(",")]
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values:
        key = str(value).strip().lower()
        if key and key in allowed and key not in cleaned:
            cleaned.append(key)
    return cleaned


@router.get("/global")
def get_global_settings(db: Session = Depends(get_db)):
    """搜索渠道的全局设置：排序优先级、Magnet 模板、搜索代理。"""
    saved = _saved_sources(db).get("global") or {}
    if not isinstance(saved, dict):
        saved = {}
    source_options = _searchable_source_options()
    allowed_sources = {item["id"] for item in source_options}
    return ok(
        {
            "search_proxy": str(saved.get("search_proxy") or ""),
            "search_proxy_username": str(saved.get("search_proxy_username") or ""),
            "search_proxy_password": str(saved.get("search_proxy_password") or ""),
            "search_source_order": _clean_order(saved.get("search_source_order"), allowed_sources),
            "resource_type_order": _clean_order(
                saved.get("resource_type_order"), set(_RESOURCE_LABELS)
            )
            or list(_RESOURCE_ORDER_DEFAULT),
            "magnet_metadata_url_template": str(
                saved.get("magnet_metadata_url_template") or _MAGNET_DEFAULT
            ),
            "source_options": source_options,
            "resource_options": _resource_options(),
        }
    )


@router.post("/global")
def save_global_settings(body: dict[str, Any], db: Session = Depends(get_db)):
    payload = body or {}
    proxy = str(payload.get("search_proxy") or "").strip()
    if proxy and not _PROXY_RE.match(proxy):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_PROXY",
                "message": "代理地址格式应为 http://host:port、https://… 或 socks5h://…",
            },
        )
    template = str(payload.get("magnet_metadata_url_template") or _MAGNET_DEFAULT).strip()
    if "{info_hash}" not in template:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_MAGNET_TEMPLATE",
                "message": "Magnet 元数据地址模板必须包含 {info_hash} 占位符",
            },
        )
    if not template.lower().startswith(("http://", "https://")):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_MAGNET_TEMPLATE",
                "message": "Magnet 元数据地址模板必须以 http:// 或 https:// 开头",
            },
        )
    saved = {
        "search_proxy": proxy,
        "search_proxy_username": str(payload.get("search_proxy_username") or "").strip(),
        "search_proxy_password": str(payload.get("search_proxy_password") or ""),
        "search_source_order": _clean_order(
            payload.get("search_source_order"),
            {item["id"] for item in _searchable_source_options()},
        ),
        "resource_type_order": _clean_order(
            payload.get("resource_type_order"), set(_RESOURCE_LABELS)
        )
        or list(_RESOURCE_ORDER_DEFAULT),
        "magnet_metadata_url_template": template,
    }
    _upsert_setting(db, "sources.global", json.dumps(saved, ensure_ascii=False))
    return ok(saved)


@router.get("/schema")
def get_source_schema(db: Session = Depends(get_db)):
    return ok(SearchSourceAdapter.schemas(_saved_sources(db)))


@router.put("")
def put_source_settings(body: dict[str, Any], db: Session = Depends(get_db)):
    valid_ids = SearchSourceAdapter.source_ids()
    for source_id, values in body.items():
        if source_id not in valid_ids or not isinstance(values, dict):
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_SOURCE_CONFIG", "message": "搜索源配置格式无效"},
            )
    saved = _saved_sources(db)
    for source_id, values in body.items():
        existing = saved.get(source_id)
        if not isinstance(existing, dict):
            existing = {"enabled": bool(existing)} if existing is not None else {}
        merged = {**existing, **values}
        row = db.get(Setting, f"sources.{source_id}")
        encoded = json.dumps(merged, ensure_ascii=False)
        if row is None:
            db.add(Setting(key=f"sources.{source_id}", value=encoded))
        else:
            row.value = encoded
            row.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return ok(SearchSourceAdapter.schemas(_saved_sources(db)))


@router.post("/test/{source_id}")
def test_source(source_id: str, db: Session = Depends(get_db)):
    if source_id not in SearchSourceAdapter.source_ids():
        raise HTTPException(
            status_code=404,
            detail={"code": "SOURCE_NOT_FOUND", "message": "搜索源不存在"},
        )
    result = SearchSourceAdapter.test_source(source_id, _vendor_config(_saved_sources(db)))
    return ok(result)


@router.get("/meta")
def source_meta(db: Session = Depends(get_db)):
    """渠道账户卡片与动态选项（账户只用缓存，避免拖慢设置页）。"""
    config = _vendor_config(_saved_sources(db))
    options: dict[str, Any] = {}
    try:
        options["pansou"] = SearchSourceAdapter.dynamic_options("pansou", "", config)
    except Exception as error:  # 动态选项失败不阻塞页面
        options["pansou"] = {"status": "unavailable", "error": str(error)}
    return ok({"accounts": SearchSourceAdapter.cached_accounts(), "options": options})


@router.post("/account/{source_id}")
def refresh_account(source_id: str, db: Session = Depends(get_db)):
    if source_id not in SearchSourceAdapter.source_ids():
        raise HTTPException(
            status_code=404,
            detail={"code": "SOURCE_NOT_FOUND", "message": "搜索源不存在"},
        )
    card = SearchSourceAdapter.account_info(
        source_id, _vendor_config(_saved_sources(db)), refresh=True
    )
    return ok(card)


@router.post("/options/{scope}/{key}")
def refresh_options(scope: str, key: str, db: Session = Depends(get_db)):
    if scope not in SearchSourceAdapter.source_ids():
        raise HTTPException(
            status_code=404,
            detail={"code": "SOURCE_NOT_FOUND", "message": "搜索源不存在"},
        )
    try:
        result = SearchSourceAdapter.dynamic_options(scope, key, _vendor_config(_saved_sources(db)))
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail={"code": "SOURCE_OPTIONS_UNSUPPORTED", "message": "该搜索源没有动态选项"},
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "SOURCE_OPTIONS_FAILED", "message": f"读取选项失败：{error}"},
        ) from error
    return ok(result)


@router.post("/hdhive/oauth/start")
def hdhive_oauth_start(body: dict[str, Any]):
    try:
        return ok(SearchSourceAdapter.hdhive_oauth_start(body))
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail={"code": "OAUTH_INVALID", "message": str(error)}
        ) from error


@router.post("/hdhive/oauth/exchange")
def hdhive_oauth_exchange(body: dict[str, Any]):
    try:
        return ok(SearchSourceAdapter.hdhive_oauth_exchange(body))
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail={"code": "OAUTH_INVALID", "message": str(error)}
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=502, detail={"code": "OAUTH_FAILED", "message": str(error)}
        ) from error
