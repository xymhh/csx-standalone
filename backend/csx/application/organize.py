"""Media library organization use case."""

from __future__ import annotations

import posixpath

from csx.domain.naming import build_media_paths

_MOVIE_TYPES = {"movie", "film", "电影"}


def is_movie(media_type: str | None) -> bool:
    return str(media_type or "").lower() in _MOVIE_TYPES


def media_type_dir(media_type: str | None, *, type_movie: str, type_tv: str) -> str:
    return type_movie if is_movie(media_type) else type_tv


def organize_file(
    drive,
    file_row: dict,
    media: dict,
    *,
    library_root: str = "",
    type_folder: bool = False,
    type_movie: str = "电影",
    type_tv: str = "电视剧",
) -> str:
    """Move and rename one transferred cloud file; return its resulting path."""
    folder, filename = build_media_paths(
        media_title=media["title"],
        media_type=media.get("type", "tv"),
        year=media.get("year"),
        season=file_row.get("season"),
        episode=file_row.get("episode"),
        quality_bucket=file_row.get("quality_bucket", "sd"),
        original_ext=file_row.get("extension", "mkv"),
        resource_kind=file_row.get("resource_kind", "episode"),
        release_date=file_row.get("release_date"),
    )
    segments = [str(library_root or "").strip().rstrip("/")]
    if type_folder:
        segments.append(
            media_type_dir(media.get("type"), type_movie=type_movie, type_tv=type_tv).strip("/")
        )
    segments.append(folder)
    target_dir = posixpath.join(*[segment for segment in segments if segment])
    target_path = posixpath.join(target_dir, filename)
    drive.move(str(file_row["file_id"]), target_dir)
    drive.rename(str(file_row["file_id"]), filename)
    return target_path
