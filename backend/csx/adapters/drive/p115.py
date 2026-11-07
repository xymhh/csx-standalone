"""115 vendor driver adapter. Vendor imports stay inside this boundary."""

from __future__ import annotations

import posixpath
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from csx.ports.drive import CloudFile, ShareFile, ShareStatus, TransferOutcome


class P115DriveAdapter:
    provider = "115"

    def __init__(self, share_service, files_service):
        self.share = share_service
        self.files = files_service
        self._known = {}

    @staticmethod
    def _share_url(share_url: str, password: str) -> str:
        if not password:
            return share_url
        parsed = urlsplit(share_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["password"] = password
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
        )

    def check_share(self, share_url: str, password: str = "") -> ShareStatus:
        status = self.share.check_share_status(self._share_url(share_url, password))
        error = str(getattr(status, "error_message", "") or "")
        return ShareStatus(
            bool(getattr(status, "is_valid", False)), error, "提取码" in error or "密码" in error
        )

    def list_share_files(self, share_url: str, password: str = "") -> list[ShareFile]:
        items = self.share.list_share_files(self._share_url(share_url, password))
        return [
            ShareFile(
                str(item.get("id", item.get("file_id", ""))),
                str(item.get("name", item.get("file_name", ""))),
                int(item.get("size", 0) or 0),
                str(item.get("sha1", "")),
                str(item.get("relative_path", item.get("name", ""))),
            )
            for item in items
        ]

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
            "" if not failed else "部分 115 文件转存失败",
        )

    def move(self, file_id: str, target_dir: str) -> None:
        known = self._known.get(str(file_id))
        item = known[0] if known else None
        moved = self.files.move_file(item, target_dir, item.name) if item else None
        if moved is None:
            raise RuntimeError(f"115 移动文件失败: {file_id}")
        self._known[str(file_id)] = (moved, target_dir)

    def rename(self, file_id: str, new_name: str) -> None:
        known = self._known.get(str(file_id))
        item, path = known if known else (None, "")
        if item is None or not self.files.rename_file(path, item, new_name):
            raise RuntimeError(f"115 重命名失败: {file_id}")
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

    def list_dir(self, path: str) -> list[CloudFile]:
        items = self.files.list_files_recursive(path)
        self._known.update({str(item.id): (item, path) for item in items})
        return [
            CloudFile(str(item.id), item.name, path, int(item.size or 0), str(item.sha1 or ""))
            for item in items
            if not item.is_directory
        ]
