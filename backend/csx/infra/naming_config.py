"""重命名模板配置解析：读 `naming` 分组，缺省回落 MoviePilot 默认模板。"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.domain.naming import DEFAULT_MOVIE_TEMPLATE, DEFAULT_TV_TEMPLATE
from csx.infra.models import Episode, Season, Setting


def _section(db: Session, name: str) -> dict:
    values: dict = {}
    for row in db.scalars(select(Setting).where(Setting.key.like(f"{name}.%"))):
        key = row.key.split(".", 1)[1]
        try:
            values[key] = json.loads(row.value)
        except (TypeError, ValueError):
            continue
    return values


def resolve_naming(db: Session) -> dict:
    """返回本次整理应使用的三套模板。"""
    config = _section(db, "naming")
    movie = str(config.get("movie_format") or "").strip() or DEFAULT_MOVIE_TEMPLATE
    tv = str(config.get("tv_format") or "").strip() or DEFAULT_TV_TEMPLATE
    variety = str(config.get("variety_format") or "").strip() or tv
    return {"movie": movie, "tv": tv, "variety": variety}


def episode_meta(db: Session, media_id: int, season: int, episode: int) -> tuple[str, int | None]:
    """返回 (单集标题, 本季总集数)，查不到时给空值。"""
    season_row = db.scalar(
        select(Season).where(Season.media_id == media_id, Season.season_number == season)
    )
    if season_row is None:
        return "", None
    rows = db.scalars(select(Episode).where(Episode.season_id == season_row.id)).all()
    title = next((row.title for row in rows if row.episode_number == episode), "") or ""
    return str(title), len(rows)
