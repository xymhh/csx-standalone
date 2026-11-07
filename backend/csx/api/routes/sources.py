"""Dynamic search-source configuration endpoints.

All routes are mounted beneath ``/api/v1`` and protected by ``auth_guard`` in
``csx.api.main`` before they can read or modify persisted source settings.
"""

from __future__ import annotations

import json
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
    config: dict[str, Any] = {}
    for source_values in saved.values():
        if isinstance(source_values, dict):
            config.update(source_values)
    return config


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
