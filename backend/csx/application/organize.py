"""Media library organization use case."""

from __future__ import annotations

import posixpath

from csx.domain.naming import build_media_paths


def organize_file(drive, file_row: dict, media: dict, *, library_root: str = "") -> str:
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
    target_dir = posixpath.join(library_root.strip("/"), folder)
    target_path = posixpath.join(target_dir, filename)
    drive.move(str(file_row["file_id"]), target_dir)
    drive.rename(str(file_row["file_id"]), filename)
    return target_path
