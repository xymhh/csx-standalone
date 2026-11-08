"""Quark vendor driver adapter. Vendor imports stay inside this boundary."""

from __future__ import annotations

import posixpath
from urllib.parse import quote

from csx.ports.drive import CloudDirectory, CloudFile, ShareFile, ShareStatus, TransferOutcome


class QuarkDriveAdapter:
    provider = "quark"

    def __init__(self, share_service, files_service):
        self.share = share_service
        self.files = files_service
        self._known = {}
        self._directory_paths = {"0": "/"}

    @staticmethod
    def _share_url(share_url: str, password: str) -> str:
        return f"{share_url} 提取码:{quote(password, safe='')}" if password else share_url

    def check_share(self, share_url: str, password: str = "") -> ShareStatus:
        status = self.share.check_share_status(self._share_url(share_url, password))
        error = str(getattr(status, "error_message", "") or "")
        share_info = getattr(status, "share_info", {}) or {}
        return ShareStatus(
            bool(getattr(status, "is_valid", False)),
            error,
            "提取码" in error,
            str(share_info.get("share_title") or ""),
        )

    def list_share_files(self, share_url: str, password: str = "") -> list[ShareFile]:
        result = []
        for item in self.share.list_share_files(self._share_url(share_url, password)):
            result.append(
                ShareFile(
                    str(item.get("id", "")),
                    str(item.get("name", "")),
                    int(item.get("size", 0) or 0),
                    str(item.get("sha1", "")),
                    str(item.get("relative_path", item.get("name", ""))),
                    bool(item.get("is_dir") or item.get("is_directory")),
                )
            )
        return result

    def transfer(self, share_url, target_dir, *, file_ids, password="", rename_map=None):
        succeeded, failed = self.share.transfer_files_batch(
            self._share_url(share_url, password), list(file_ids), target_dir
        )
        files = self.files.list_files_recursive(target_dir)
        self._known.update({str(item.id): (item, target_dir) for item in files})
        created = [
            (
                str(item.id),
                f"{target_dir.rstrip('/')}/{item.name}",
                int(item.size or 0),
                str(item.sha1 or ""),
            )
            for item in files
            if not item.is_directory
        ]
        ok = len(succeeded) == len(file_ids) and not failed
        return TransferOutcome(
            ok,
            [str(item) for item in failed],
            created,
            "" if not failed else "部分夸克文件转存失败",
        )

    def move(self, file_id: str, target_dir: str) -> None:
        known = self._known.get(str(file_id))
        item = known[0] if known else None
        moved = self.files.move_file(item, target_dir, item.name) if item else None
        if moved is None:
            raise RuntimeError(f"夸克移动文件失败: {file_id}")
        self._known[str(file_id)] = (moved, target_dir)

    def rename(self, file_id: str, new_name: str) -> None:
        known = self._known.get(str(file_id))
        item, path = known if known else (None, "")
        if item is None or not self.files.rename_file(path, item, new_name):
            raise RuntimeError(f"夸克重命名失败: {file_id}")
        self._known[str(file_id)] = (item, path)

    def get_download_url(self, path: str) -> str:
        directory, filename = posixpath.split(str(path))
        item = self.files.find_file(directory or "/", filename)
        if item is None:
            raise FileNotFoundError(f"云盘文件不存在：{path}")
        url, _headers = self.files.resolve_download_link(item)
        if not url:
            raise RuntimeError(f"未获得文件直链：{path}")
        return str(url)

    def resolve_download_link(self, path: str) -> str:
        return self.get_download_url(path)

    def delete_path(self, path: str) -> bool:
        directory, filename = posixpath.split(str(path))
        item = self.files.find_file(directory or "/", filename)
        if item is None or item.is_directory:
            return False
        return bool(self.files.delete_file(item.id))

    def delete_empty_directory(self, path: str) -> bool:
        directory, name = posixpath.split(str(path).rstrip("/"))
        item = self.files.find_file(directory or "/", name)
        if item is None or not item.is_directory or self.files._list(item.id):
            return False
        return bool(self.files.delete_file(item.id))

    def list_dir(self, path: str) -> list[CloudFile]:
        lookup = self.files.resolve_directory(path)
        if not lookup.checked or lookup.directory_id is None:
            raise RuntimeError(f"无法读取夸克目录：{path}")
        root = str(path).rstrip("/") or "/"
        result = []
        queue = [(str(lookup.directory_id), root)]
        while queue:
            parent_id, parent_path = queue.pop()
            for item in self.files._list(parent_id):
                item_path = posixpath.join(parent_path, item.name)
                if item.is_directory:
                    queue.append((item.id, item_path))
                    continue
                self._known[str(item.id)] = (item, parent_path)
                result.append(
                    CloudFile(
                        str(item.id), item.name, item_path, int(item.size or 0), str(item.sha1 or "")
                    )
                )
        return result

    def list_directories(self, parent_id: str = "") -> list[CloudDirectory]:
        parent_id = str(parent_id or "0")
        parent_path = self._directory_paths.get(parent_id, "/")
        directories = [item for item in self.files._list(parent_id) if item.is_directory]
        result = []
        for item in directories:
            path = posixpath.join(parent_path, item.name)
            self._directory_paths[item.id] = path
            has_children = any(child.is_directory for child in self.files._list(item.id))
            result.append(CloudDirectory(item.id, item.name, path, has_children))
        return result
