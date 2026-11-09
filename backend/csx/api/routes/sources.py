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


@router.get("/global")
def get_global_settings(db: Session = Depends(get_db)):
    """搜索渠道的全局网络设置（当前只有代理）。"""
    saved = _saved_sources(db).get("global") or {}
    if not isinstance(saved, dict):
        saved = {}
    return ok({"search_proxy": str(saved.get("search_proxy") or "")})


@router.post("/global")
def save_global_settings(body: dict[str, Any], db: Session = Depends(get_db)):
    proxy = str((body or {}).get("search_proxy") or "").strip()
    if proxy and not _PROXY_RE.match(proxy):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_PROXY",
                "message": "代理地址格式应为 http://host:port、https://… 或 socks5h://…",
            },
        )
    payload = json.dumps({"search_proxy": proxy}, ensure_ascii=False)
    _upsert_setting(db, "sources.global", payload)
    return ok({"search_proxy": proxy})


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
