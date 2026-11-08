"""重命名模板配置与实时预览（对齐 MoviePilot 的 Jinja2 模板方案）。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from csx.api.envelope import ok
from csx.application.naming import (
    NamingError,
    build_context,
    render_relative_path,
    select_template,
    split_relative_path,
)
from csx.domain.naming import DEFAULT_MOVIE_TEMPLATE, DEFAULT_TV_TEMPLATE
from csx.infra.db import get_db
from csx.infra.models import Setting
from csx.infra.naming_config import resolve_naming

router = APIRouter(prefix="/naming", tags=["naming"])

VARIABLES = [
    {"name": "title", "label": "片名（中文）", "example": "示例电影", "group": "基础"},
    {"name": "year", "label": "年份", "example": "2024", "group": "基础"},
    {"name": "title_year", "label": "片名 (年份)", "example": "示例电影 (2024)", "group": "基础"},
    {"name": "type", "label": "类型（电影/电视剧）", "example": "电影", "group": "基础"},
    {"name": "tmdbid", "label": "TMDB ID", "example": "693134", "group": "基础"},
    {"name": "season", "label": "季号（数字）", "example": "1", "group": "剧集"},
    {"name": "season_fmt", "label": "季号 Sxx", "example": "S01", "group": "剧集"},
    {"name": "season_episode", "label": "季集 SxxExx", "example": "S01E01", "group": "剧集"},
    {"name": "episode", "label": "集号（数字）", "example": "1", "group": "剧集"},
    {"name": "episode_title", "label": "单集标题", "example": "第一集", "group": "剧集"},
    {"name": "episode_date", "label": "播出日期", "example": "2024-01-01", "group": "剧集"},
    {"name": "total_episodes", "label": "本季总集数", "example": "12", "group": "剧集"},
    {"name": "fileExt", "label": "文件后缀（含点）", "example": ".mkv", "group": "技术"},
    {"name": "videoFormat", "label": "分辨率", "example": "2160p", "group": "技术"},
    {"name": "part", "label": "分段（CD1/上）", "example": "CD1", "group": "技术"},
]

_SAMPLE_MOVIE = {
    "title": "示例电影",
    "year": 2024,
    "media_type": "movie",
    "season": None,
    "episode": None,
    "extension": "mkv",
    "quality_bucket": "1080p",
    "tmdb_id": 693134,
}
_SAMPLE_TV = {
    "title": "示例剧集",
    "year": 2024,
    "media_type": "tv",
    "season": 1,
    "episode": 1,
    "episode_title": "第一集",
    "total_episodes": 12,
    "extension": "mkv",
    "quality_bucket": "4k",
    "tmdb_id": 12345,
}


class NamingBody(BaseModel):
    movie_format: str = Field(default="", max_length=1024)
    tv_format: str = Field(default="", max_length=1024)
    variety_format: str = Field(default="", max_length=1024)


class PreviewBody(BaseModel):
    template: str | None = Field(default=None, max_length=1024)
    media_type: str = "tv"
    title: str = Field(default="示例剧集", max_length=200)
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    episode_title: str = ""
    total_episodes: int | None = None
    extension: str = "mkv"
    quality_bucket: str = "1080p"
    part: str | None = None


def _validate(label: str, template: str, sample: dict) -> None:
    if not template.strip():
        raise HTTPException(
            422, detail={"code": "NAMING_TEMPLATE_EMPTY", "message": f"{label}模板不能为空"}
        )
    try:
        render_relative_path(template, build_context(**sample))
    except NamingError as error:
        raise HTTPException(
            422, detail={"code": "NAMING_TEMPLATE_INVALID", "message": f"{label}：{error}"}
        ) from error


def _save(db: Session, key: str, value: str) -> None:
    row = db.get(Setting, f"naming.{key}")
    encoded = json.dumps(value, ensure_ascii=False)
    if row is None:
        db.add(Setting(key=f"naming.{key}", value=encoded))
    else:
        row.value = encoded


@router.get("")
def get_naming(db: Session = Depends(get_db)):
    current = resolve_naming(db)
    return ok(
        {
            "movie_format": current["movie"],
            "tv_format": current["tv"],
            "variety_format": current["variety"],
            "defaults": {
                "movie_format": DEFAULT_MOVIE_TEMPLATE,
                "tv_format": DEFAULT_TV_TEMPLATE,
                "variety_format": DEFAULT_TV_TEMPLATE,
            },
            "variables": VARIABLES,
        }
    )


@router.put("")
def put_naming(body: NamingBody, db: Session = Depends(get_db)):
    movie = body.movie_format.strip() or DEFAULT_MOVIE_TEMPLATE
    tv = body.tv_format.strip() or DEFAULT_TV_TEMPLATE
    variety = body.variety_format.strip() or tv
    _validate("电影", movie, _SAMPLE_MOVIE)
    _validate("剧集", tv, _SAMPLE_TV)
    _validate("综艺", variety, _SAMPLE_TV)
    _save(db, "movie_format", movie)
    _save(db, "tv_format", tv)
    _save(db, "variety_format", variety)
    db.commit()
    return get_naming(db)


@router.post("/preview")
def preview(body: PreviewBody, db: Session = Depends(get_db)):
    template = body.template
    if not template:
        template = select_template(
            resolve_naming(db), "movie" if body.media_type == "movie" else "tv"
        )
    context = build_context(
        title=body.title,
        year=body.year,
        media_type=body.media_type,
        season=body.season,
        episode=body.episode,
        episode_title=body.episode_title,
        total_episodes=body.total_episodes,
        extension=body.extension,
        quality_bucket=body.quality_bucket,
        part=body.part,
    )
    try:
        relative = render_relative_path(template, context)
    except NamingError as error:
        return ok({"valid": False, "message": str(error), "relative_path": ""})
    folder, filename = split_relative_path(relative)
    return ok(
        {
            "valid": True,
            "message": "",
            "relative_path": relative,
            "folder": folder,
            "filename": filename,
        }
    )
