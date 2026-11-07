"""Pure media naming rules and filename episode parsing."""

from __future__ import annotations

import re
from datetime import date

_INVALID = re.compile(r"[/\\:*?\"<>|]+")
_SPACE = re.compile(r"\s+")
_EPISODE_PATTERNS = (
    re.compile(r"(?i)S(?P<season>\d{1,3})[ ._-]*E(?:P)?[ ._-]*(?P<episode>\d{1,4})\b"),
    re.compile(r"(?i)\bE(?:P)?[ ._-]*(?P<episode>\d{1,4})\b"),
    re.compile(r"(?i)\bEPISODE[ ._-]*(?P<episode>\d{1,4})\b"),
    re.compile(r"第\s*(?P<season>\d{1,3})\s*季\s*第\s*(?P<episode>\d{1,4})\s*集"),
    re.compile(r"第\s*(?P<episode>\d{1,4})\s*集"),
)
_QUALITY_LABELS = {"remux": "REMUX", "dv": "DV", "hdr": "HDR"}


def _clean(value: str) -> str:
    cleaned = _SPACE.sub(" ", _INVALID.sub(" ", str(value or "")))
    return cleaned.strip(" .")[:200].rstrip(" .")


def parse_episode_from_name(text: str) -> tuple[int | None, int | None]:
    """Parse season and episode from common Chinese and SxxExx filename forms."""
    try:
        for pattern in _EPISODE_PATTERNS:
            match = pattern.search(str(text or ""))
            if match:
                season = match.groupdict().get("season")
                return (int(season) if season else None, int(match.group("episode")))
    except (TypeError, ValueError):
        return None, None
    return None, None


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
