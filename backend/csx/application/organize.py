"""Media library organization use case."""

from __future__ import annotations

import logging
import posixpath

from csx.application.naming import (
    NamingError,
    build_context,
    render_relative_path,
    split_relative_path,
)
from csx.domain.naming import build_media_paths

_MOVIE_TYPES = {"movie", "film", "电影"}

logger = logging.getLogger(__name__)


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
    template: str | None = None,
    episode_title: str = "",
    total_episodes: int | None = None,
) -> str:
    """Move and rename one transferred cloud file; return its resulting path.

    ``template`` 为 MoviePilot 风格 Jinja2 模板；为空或渲染失败时回退旧格式，
    保证整理任务不会因模板问题直接失败。
    """
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
    if template:
        try:
            context = build_context(
                title=media["title"],
                year=media.get("year"),
                media_type=media.get("type", "tv"),
                tmdb_id=media.get("tmdb_id"),
                season=file_row.get("season"),
                episode=file_row.get("episode"),
                episode_title=episode_title,
                episode_date=file_row.get("release_date"),
                total_episodes=total_episodes,
                extension=file_row.get("extension", "mkv"),
                quality_bucket=file_row.get("quality_bucket", "sd"),
                part=file_row.get("part"),
            )
            folder, filename = split_relative_path(render_relative_path(template, context))
        except NamingError as error:
            logger.warning("重命名模板不可用，回退旧格式：%s", error)
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
