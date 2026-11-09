"""二级分类策略的读取与规整。"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.domain.category import default_strategies
from csx.infra.models import Setting


def _section(db: Session, name: str) -> dict[str, Any]:
    rows = db.scalars(select(Setting).where(Setting.key.like(f"{name}.%")))
    values: dict[str, Any] = {}
    for row in rows:
        key = row.key.split(".", 1)[1]
        try:
            values[key] = json.loads(row.value)
        except (TypeError, ValueError):
            continue
    return values


def normalize_strategies(raw: Any) -> list[dict[str, Any]]:
    """把前端/旧数据规整成 [{name, conditions}]，丢弃脏条目。"""
    if not isinstance(raw, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        conditions = item.get("conditions")
        if not isinstance(conditions, dict):
            conditions = {}
        cleaned.append(
            {
                "name": name,
                "conditions": {
                    str(key): str(value).strip()
                    for key, value in conditions.items()
                    if value not in (None, "")
                },
            }
        )
    return cleaned


def resolve_category_strategies(db: Session) -> dict[str, list[dict[str, Any]]]:
    """返回电影/剧集两套策略；未配置时用 MoviePilot 默认值。"""
    config = _section(db, "category")
    if config.get("enabled") is False:
        return {"movie": [], "tv": []}
    movie = normalize_strategies(config.get("movie")) or default_strategies("movie")
    tv = normalize_strategies(config.get("tv")) or default_strategies("tv")
    return {"movie": movie, "tv": tv}
