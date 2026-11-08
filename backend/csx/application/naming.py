"""MoviePilot 风格命名模板渲染（应用层，唯一依赖 jinja2 的位置）。"""

from __future__ import annotations

import posixpath

from jinja2 import ChainableUndefined
from jinja2.sandbox import SandboxedEnvironment

from csx.domain.naming import (
    DEFAULT_MOVIE_TEMPLATE,
    DEFAULT_TV_TEMPLATE,
    clean_segment,
    normalize_relative_path,
)

_ENV = SandboxedEnvironment(undefined=ChainableUndefined, autoescape=False)

_MOVIE_TYPES = {"movie", "film", "电影"}
_VARIETY_KINDS = {"variety", "综艺"}

# quality_bucket → MoviePilot 的 videoFormat（分辨率写法）
_VIDEO_FORMATS = {
    "4k": "2160p",
    "2160p": "2160p",
    "1080p": "1080p",
    "hd": "1080p",
    "720p": "720p",
    "remux": "2160p",
    "dv": "2160p",
    "hdr": "2160p",
}


class NamingError(ValueError):
    """模板不可用（语法错误、渲染为空、路径非法）。消息可直接展示给用户。"""


def is_movie_type(media_type: str | None) -> bool:
    return str(media_type or "").lower() in _MOVIE_TYPES


def video_format(quality_bucket: str | None) -> str:
    return _VIDEO_FORMATS.get(str(quality_bucket or "").lower(), "")


def select_template(naming: dict | None, media_type: str | None, resource_kind: str | None = None):
    """按媒体类型/资源类型选模板：综艺可单独配，缺省回落剧集模板。"""
    config = naming or {}
    movie = str(config.get("movie") or DEFAULT_MOVIE_TEMPLATE)
    tv = str(config.get("tv") or DEFAULT_TV_TEMPLATE)
    variety = str(config.get("variety") or tv)
    if is_movie_type(media_type):
        return movie
    if str(resource_kind or "").lower() in _VARIETY_KINDS:
        return variety
    return tv


def build_context(
    *,
    title: str,
    year: int | None = None,
    media_type: str | None = "tv",
    tmdb_id: int | None = None,
    season: int | None = None,
    episode: int | str | None = None,
    episode_title: str | None = None,
    episode_date: object = None,
    total_episodes: int | None = None,
    extension: str = "mkv",
    quality_bucket: str = "sd",
    part: str | None = None,
) -> dict:
    """装配模板上下文，字段名与 MoviePilot 的 TemplateContextBuilder 对齐。"""
    clean_title = clean_segment(str(title or ""))
    year_value = int(year) if year else None
    season_value = int(season) if season is not None else None
    ext = str(extension or "").strip().lstrip(".").lower()
    context = {
        "title": clean_title,
        "year": year_value,
        "title_year": f"{clean_title} ({year_value})" if year_value else clean_title,
        "type": "电影" if is_movie_type(media_type) else "电视剧",
        "tmdbid": tmdb_id,
        "season": season_value,
        "season_fmt": f"S{season_value:02d}" if season_value is not None else "",
        "season_episode": (
            f"S{season_value:02d}E{int(episode):02d}"
            if season_value is not None and episode is not None
            else ""
        ),
        "episode": episode,
        "episode_title": clean_segment(str(episode_title or "")),
        "episode_date": episode_date,
        "total_episodes": total_episodes,
        "part": clean_segment(str(part or "")),
        "fileExt": f".{ext}" if ext else "",
        "videoFormat": video_format(quality_bucket),
    }
    return {key: value for key, value in context.items() if value is not None}


def render_relative_path(template: str, context: dict) -> str:
    """渲染成相对路径（含目录层级），失败抛 :class:`NamingError`。"""
    source = str(template or "").strip()
    if not source:
        raise NamingError("重命名模板为空")
    if not str(context.get("title") or "").strip():
        raise NamingError("片名缺失，无法套用重命名模板")
    try:
        rendered = _ENV.from_string(source).render(**context)
    except Exception as error:  # jinja2 语法/渲染错误都转成用户可读消息
        raise NamingError(f"模板语法错误：{error}") from error
    try:
        return normalize_relative_path(rendered)
    except ValueError as error:
        raise NamingError(str(error)) from error


def split_relative_path(relative: str) -> tuple[str, str]:
    """拆成 (目录, 文件名)。"""
    directory, filename = posixpath.split(relative)
    return directory, filename
