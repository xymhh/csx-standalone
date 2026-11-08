"""Plan canonical library paths for files found in a drive staging area."""

from __future__ import annotations

import posixpath
import re
from collections.abc import Iterable
from pathlib import PurePosixPath
from typing import Any

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
    files: Iterable[Any], media_items: Iterable[Any], library_root: str
) -> dict[str, list[dict[str, Any]]]:
    """Return matched and unrecognized drive files without performing I/O."""
    media = list(media_items)
    matched: list[dict[str, Any]] = []
    unrecognized: list[dict[str, Any]] = []
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
        target_path = posixpath.join(str(library_root).rstrip("/"), folder, target_name)
        row.update(
            {
                "recognized": True,
                "media_id": int(item.id),
                "title": item.title,
                "season": season,
                "episode": episode,
                "quality_bucket": bucket,
                "target_path": target_path,
            }
        )
        matched.append(row)
    return {"matched": matched, "unrecognized": unrecognized}
