"""Plan canonical library paths for files found in a drive staging area."""

from __future__ import annotations

import posixpath
import re
from collections.abc import Iterable
from pathlib import PurePosixPath
from typing import Any

from csx.application.naming import (
    NamingError,
    build_context,
    render_relative_path,
    select_template,
    split_relative_path,
)
from csx.application.organize import media_type_dir, resolve_category
from csx.domain.naming import build_media_paths, parse_episode_from_name

VIDEO_EXTENSIONS = {"mkv", "mp4", "avi", "mov", "wmv", "ts", "m2ts", "webm", "flv"}
SUBTITLE_EXTENSIONS = {"srt", "ass", "ssa", "sup", "sub", "idx"}
QUALITY_PATTERNS = (
    ("remux", re.compile(r"(?i)remux")),
    ("dv", re.compile(r"(?i)(?:\bdv\b|dolby[ ._-]*vision)")),
    ("hdr", re.compile(r"(?i)\bhdr(?:10)?\b")),
    ("4k", re.compile(r"(?i)(?:2160p|4k)")),
    ("hd", re.compile(r"(?i)(?:1080p|720p)")),
)


def _fold(value: str) -> str:
    return re.sub(r"[^\w\u3400-\u9fff]", "", value.casefold())


def _quality(name: str) -> str:
    for bucket, pattern in QUALITY_PATTERNS:
        if pattern.search(name):
            return bucket
    return "sd"


def plan_organize(
    files: Iterable[Any],
    media_items: Iterable[Any],
    library_root: str,
    *,
    type_folder: bool = False,
    type_movie: str = "电影",
    type_tv: str = "电视剧",
    naming: dict | None = None,
    episode_meta_for: Any = None,
    categories: dict | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Return matched and unrecognized drive files without performing I/O."""
    media = list(media_items)
    matched: list[dict[str, Any]] = []
    unrecognized: list[dict[str, Any]] = []
    warnings: list[str] = []
    category_cache: dict[int, str] = {}

    def _category(item) -> str:
        media_id = int(item.id)
        if media_id not in category_cache:
            category_cache[media_id] = resolve_category(
                {"type": item.type, "tmdb_id": getattr(item, "tmdb_id", None), "year": item.year},
                categories,
            )
        return category_cache[media_id]

    for file in files:
        name = str(getattr(file, "name", ""))
        source_path = str(getattr(file, "path", "") or name)
        ext = PurePosixPath(name).suffix.lstrip(".").lower()
        if ext not in VIDEO_EXTENSIONS | SUBTITLE_EXTENSIONS:
            continue
        row: dict[str, Any] = {
            "file_id": str(getattr(file, "file_id", "")),
            "name": name,
            "source_path": source_path,
            "size": int(getattr(file, "size", 0) or 0),
            "is_subtitle": ext in SUBTITLE_EXTENSIONS,
        }
        if ext in SUBTITLE_EXTENSIONS:
            row.update({"recognized": False, "reason": "字幕文件随视频整理"})
            unrecognized.append(row)
            continue
        stem = PurePosixPath(name).stem
        season, episode = parse_episode_from_name(stem)
        folded = _fold(stem)
        candidates = [
            item for item in media if _fold(str(item.title)) and _fold(str(item.title)) in folded
        ]
        item = max(candidates, key=lambda value: len(_fold(str(value.title))), default=None)
        if item is None or (item.type not in {"movie", "film", "电影"} and episode is None):
            row.update({"recognized": False, "reason": "无法匹配片名或季集"})
            unrecognized.append(row)
            continue
        bucket = _quality(stem)
        season = season or 1
        episode = episode or 1
        folder, target_name = build_media_paths(
            item.title,
            item.type,
            item.year,
            season,
            episode,
            bucket,
            ext,
            "video",
        )
        template = select_template(naming, item.type)
        episode_title = ""
        total_episodes = None
        if episode_meta_for is not None:
            try:
                episode_title, total_episodes = episode_meta_for(int(item.id), season, episode)
            except Exception:  # 预览阶段查不到单集信息不影响整理
                episode_title, total_episodes = "", None
        if template:
            try:
                context = build_context(
                    title=item.title,
                    year=item.year,
                    media_type=item.type,
                    tmdb_id=getattr(item, "tmdb_id", None),
                    season=season,
                    episode=episode,
                    episode_title=episode_title,
                    total_episodes=total_episodes,
                    extension=ext,
                    quality_bucket=bucket,
                )
                folder, target_name = split_relative_path(render_relative_path(template, context))
            except NamingError as error:
                warnings.append(f"{name}：{error}，已回退旧格式")
        target_path = posixpath.join(
            str(library_root).rstrip("/"),
            media_type_dir(item.type, type_movie=type_movie, type_tv=type_tv)
            if type_folder
            else "",
            _category(item),
            folder,
            target_name,
        )
        row.update(
            {
                "recognized": True,
                "media_id": int(item.id),
                "title": item.title,
                "season": season,
                "episode": episode,
                "quality_bucket": bucket,
                "target_path": target_path,
                "episode_title": episode_title,
            }
        )
        matched.append(row)
    return {"matched": matched, "unrecognized": unrecognized, "warnings": warnings}
