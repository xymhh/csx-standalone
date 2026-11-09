"""Pure media naming rules and filename episode parsing."""

from __future__ import annotations

import re
from datetime import date

_INVALID = re.compile(r"[/\\:*?\"<>|]+")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")
_SPACE = re.compile(r"\s+")

# MoviePilot 默认模板（app/core/config.py MOVIE_RENAME_FORMAT / TV_RENAME_FORMAT）
DEFAULT_MOVIE_TEMPLATE = (
    "{{title}}{% if year %} ({{year}}){% endif %}"
    "/{{title}}{% if year %} ({{year}}){% endif %}"
    "{% if part %}-{{part}}{% endif %}"
    "{% if videoFormat %} - {{videoFormat}}{% endif %}{{fileExt}}"
)
DEFAULT_TV_TEMPLATE = (
    "{{title}}{% if year %} ({{year}}){% endif %}"
    "/Season {{season}}"
    "/{{title}} - {{season_episode}}"
    "{% if part %}-{{part}}{% endif %}"
    "{% if episode %} - 第 {{episode}} 集{% endif %}{{fileExt}}"
)
MAX_TEMPLATE_LENGTH = 512
_EPISODE_PATTERNS = (
    re.compile(r"(?i)S(?P<season>\d{1,3})[ ._-]*E(?:P)?[ ._-]*(?P<episode>\d{1,4})\b"),
    # 纯数字文件名：中文剧集分享常见 "10.mkv" / "第10集.mkv" / stem "10"
    re.compile(r"^\s*0*(?P<episode>\d{1,4})\s*(\.(?:mkv|mp4|ts|avi|rmvb|flv|mov|wmv))?\s*$"),
    re.compile(r"(?i)\bE(?:P)?[ ._-]*(?P<episode>\d{1,4})\b"),
    re.compile(r"(?i)\bEPISODE[ ._-]*(?P<episode>\d{1,4})\b"),
    re.compile(r"第\s*(?P<season>\d{1,3})\s*季\s*第\s*(?P<episode>\d{1,4})\s*集"),
    re.compile(r"第\s*(?P<episode>\d{1,4})\s*集"),
)
_QUALITY_LABELS = {"remux": "REMUX", "dv": "DV", "hdr": "HDR"}


def _clean(value: str) -> str:
    cleaned = _SPACE.sub(" ", _INVALID.sub(" ", str(value or "")))
    return cleaned.strip(" .")[:200].rstrip(" .")


# 纯数字 stem 里这些值不是集数：年份与常见分辨率
_NON_EPISODE_NUMBERS = {480, 576, 720, 1080, 1440, 2160, 4320}


def _looks_like_year(value: int) -> bool:
    return 1900 <= value <= 2100


def parse_episode_from_name(text: str) -> tuple[int | None, int | None]:
    """Parse season and episode from common Chinese and SxxExx filename forms."""
    try:
        for pattern in _EPISODE_PATTERNS:
            match = pattern.search(str(text or ""))
            if match:
                season = match.groupdict().get("season")
                episode = int(match.group("episode"))
                if season is None and (
                    _looks_like_year(episode) or episode in _NON_EPISODE_NUMBERS
                ):
                    # "2024.mkv" / "1080" 不是集数，继续尝试后续模式
                    continue
                return (int(season) if season else None, episode)
    except (TypeError, ValueError):
        return None, None
    return None, None


def clean_segment(value: str) -> str:
    """清洗单个路径段：替换非法字符、压缩空白、去掉首尾空格与点。"""
    text = _CONTROL.sub(" ", str(value or ""))
    text = _SPACE.sub(" ", _INVALID.sub(" ", text))
    return text.strip(" .")[:200].rstrip(" .")


def normalize_relative_path(rendered: str) -> str:
    """校验模板渲染结果并规范成相对 POSIX 路径。

    规则：至少一级目录、不允许空段/``.``/``..``、每段清洗非法字符、总长上限。
    不合法时抛 ``ValueError``（消息面向用户，可直接展示）。
    """
    text = str(rendered or "").replace("\\", "/").strip()
    if not text:
        raise ValueError("模板渲染结果为空，请检查模板是否包含 {{title}}")
    if len(text) > MAX_TEMPLATE_LENGTH:
        raise ValueError(f"模板渲染结果超过 {MAX_TEMPLATE_LENGTH} 字符，请精简模板")
    segments = [part.strip() for part in text.strip("/").split("/")]
    if any(part in {"", ".", ".."} for part in segments):
        raise ValueError("模板路径包含空目录、`.` 或 `..`，请检查斜杠用法")
    cleaned = [clean_segment(part) for part in segments]
    if any(not part for part in cleaned):
        raise ValueError("模板渲染后存在空目录名，请检查变量是否为空")
    if len(cleaned) < 2:
        raise ValueError("模板至少要有一级目录，例如 `{{title}}/{{title}}{{fileExt}}`")
    return "/".join(cleaned)


def build_media_paths(
    media_title: str,
    media_type: str,
    year: int | None,
    season: int | None,
    episode: int | None,
    quality_bucket: str,
    original_ext: str,
    resource_kind: str,
    *,
    release_date: date | None = None,
) -> tuple[str, str]:
    """Return relative POSIX folder and filename for one media resource."""
    title = _clean(media_title) or "Untitled"
    year_suffix = f" ({int(year):04d})" if year else ""
    ext = str(original_ext or "").strip().lstrip(".")
    ext = _clean(ext).replace(" ", "") or "mkv"
    quality = _QUALITY_LABELS.get(str(quality_bucket or "").lower())
    marker = f" [{quality}]" if quality else ""
    is_variety = str(resource_kind or "").lower() in {"variety", "综艺"}
    is_movie = str(media_type or "").lower() in {"movie", "film", "电影"}
    folder = f"{title}{year_suffix}"
    if is_movie:
        filename = f"{title}{year_suffix}{marker}.{ext}"
        return _clean(folder), _clean(filename)
    ss, ee = max(1, int(season or 1)), max(1, int(episode or 1))
    if is_variety:
        if release_date:
            filename = f"{title} - S{ss:02d}E{ee:02d} ({release_date:%Y-%m-%d}){marker}.{ext}"
        else:
            filename = f"{title} - E{ee:02d}{marker}.{ext}"
    elif year:
        filename = f"{title}{year_suffix} S{ss:02d}E{ee:02d}{marker}.{ext}"
    else:
        filename = f"{title} S{ss:02d}E{ee:02d}{marker}.{ext}"
    if is_variety:
        return _clean(folder), _clean(filename)
    return f"{_clean(folder)}/Season {ss:02d}", _clean(filename)
