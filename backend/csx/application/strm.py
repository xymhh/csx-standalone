"""STRM content and file synchronization use case."""

from __future__ import annotations

import posixpath
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote


@dataclass(frozen=True)
class StrmSyncResult:
    generated: int
    unchanged: int
    removed: int
    errors: tuple[dict[str, Any], ...]


def _relative_media_path(value: str) -> str:
    normalized = posixpath.normpath(str(value or "")).lstrip("/")
    if normalized in {"", "."} or normalized == ".." or normalized.startswith("../"):
        raise ValueError("媒体库路径无效")
    return normalized


def build_strm_content(
    library_path: str,
    *,
    mode: str,
    local_mount_root: str = "",
    url_template: str = "",
    direct_url: str = "",
    library_file_id: int | None = None,
) -> str:
    """Build one STRM target from a local mount, URL template, or resolved URL."""
    relative = _relative_media_path(library_path)
    normalized_mode = mode.strip().lower().replace("-", "_")
    if normalized_mode in {"local_mount", "mount", "clouddrive2", "alist"}:
        if not local_mount_root:
            raise ValueError("local_mount_root 未配置")
        return posixpath.join(local_mount_root.rstrip("/"), relative)
    if normalized_mode == "direct":
        if not direct_url:
            raise ValueError("无法解析网盘直链")
        return direct_url
    if normalized_mode in {"template", "proxy", "proxy_url"}:
        if not url_template:
            raise ValueError("url_template 未配置")
        try:
            return url_template.format(
                path=quote(relative, safe="/"),
                library_file_id=library_file_id or "",
                filename=quote(posixpath.basename(relative), safe=""),
            )
        except (KeyError, ValueError) as error:
            raise ValueError(f"STRM URL 模板无效：{error}") from error
    raise ValueError(f"不支持的 STRM 模式：{mode}")


class StrmService:
    def __init__(
        self,
        repository: Any,
        *,
        strm_settings: Mapping[str, Any],
        drives: Mapping[str, Any] | None = None,
        url_resolver: Callable[[Mapping[str, Any], Mapping[str, Any]], str] | None = None,
    ) -> None:
        self.repository = repository
        self.config = dict(strm_settings)
        self.drives = dict(drives or {})
        self.url_resolver = url_resolver or self._resolve_direct_url

    def _resolve_direct_url(self, row: Mapping[str, Any], config: Mapping[str, Any]) -> str:
        provider = str(row.get("provider") or "").lower()
        drive = self.drives.get(provider)
        if drive is None or not hasattr(drive, "get_download_url"):
            raise ValueError(f"未配置 {provider or 'unknown'} 网盘直链适配器")
        return str(drive.get_download_url(str(row["path"])))

    def sync(
        self,
        *,
        library_file_id: int | None = None,
        clean_missing: bool = False,
    ) -> StrmSyncResult:
        root_value = str(self.config.get("strm_root") or "").strip()
        if not root_value:
            raise ValueError("strm_root 未配置")
        root = Path(root_value).expanduser()
        mode = str(self.config.get("mode") or "local_mount")
        generated = unchanged = removed = 0
        errors: list[dict[str, Any]] = []
        rows = self.repository.list_library_files(library_file_id=library_file_id)
        valid_ids = {int(row["id"]) for row in rows}
        for row in rows:
            try:
                relative = _relative_media_path(str(row["path"]))
                relative_strm = posixpath.splitext(relative)[0] + ".strm"
                output = root.joinpath(*relative_strm.split("/"))
                output.parent.mkdir(parents=True, exist_ok=True)
                direct_url = (
                    self.url_resolver(row, self.config) if mode.strip().lower() == "direct" else ""
                )
                content = build_strm_content(
                    str(row["path"]),
                    mode=mode,
                    local_mount_root=str(self.config.get("local_mount_root") or ""),
                    url_template=str(self.config.get("url_template") or ""),
                    direct_url=direct_url,
                    library_file_id=int(row["id"]),
                )
                rendered = content.rstrip("\r\n") + "\n"
                old = output.read_text(encoding="utf-8") if output.exists() else None
                if old != rendered:
                    output.write_text(rendered, encoding="utf-8")
                    generated += 1
                else:
                    unchanged += 1
                self.repository.upsert_record(int(row["id"]), str(output))
            except Exception as error:
                errors.append({"library_file_id": int(row["id"]), "error": str(error)})
        if clean_missing:
            for record in self.repository.list_records(library_file_id=library_file_id):
                if int(record["library_file_id"]) in valid_ids:
                    continue
                try:
                    Path(record["strm_path"]).unlink(missing_ok=True)
                    self.repository.delete_record(int(record["id"]))
                    removed += 1
                except OSError as error:
                    errors.append(
                        {"library_file_id": record["library_file_id"], "error": str(error)}
                    )
        return StrmSyncResult(generated, unchanged, removed, tuple(errors))
