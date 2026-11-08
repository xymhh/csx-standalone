"""115 vendor driver adapter. Vendor imports stay inside this boundary."""

from __future__ import annotations

import posixpath
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from csx.ports.drive import CloudDirectory, CloudFile, ShareFile, ShareStatus, TransferOutcome


class P115DriveAdapter:
    provider = "115"

    def __init__(self, share_service, files_service):
        self.share = share_service
        self.files = files_service
        self._known = {}
        self._directory_paths = {"0": "/"}

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
            bool(getattr(status, "is_valid", False)),
            error,
            "提取码" in error or "密码" in error,
            str((getattr(status, "share_info", {}) or {}).get("share_title") or ""),
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
                bool(item.get("is_dir") or item.get("is_directory")),
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

    def resolve_download_link(self, path: str) -> str:
        return self.get_download_url(path)

    def delete_path(self, path: str) -> bool:
        directory, filename = posixpath.split(str(path))
        item = self.files.find_file(directory or "/", filename)
        if item is None or item.is_directory:
            return False
        return bool(self.files.manager.delete_file(item.id))

    def delete_empty_directory(self, path: str) -> bool:
        directory, name = posixpath.split(str(path).rstrip("/"))
        item = self.files.find_file(directory or "/", name)
        if item is None or not item.is_directory:
            return False
        checked, children = self.files.manager.list_files_by_cid_checked(item.id)
        return bool(checked and not children and self.files.manager.delete_file(item.id))

    def list_dir(self, path: str) -> list[CloudFile]:
        items = self.files.list_files_recursive(path)
        result = []
        for item in items:
            raw = item.native if isinstance(item.native, dict) else {}
            parent_path = str(raw.get("_cloud_dir") or path).rstrip("/") or "/"
            file_path = posixpath.join(parent_path, item.name)
            self._known[str(item.id)] = (item, parent_path)
            result.append(CloudFile(str(item.id), item.name, file_path, int(item.size or 0), item.sha1))
        return result

    def list_directories(self, parent_id: str = "") -> list[CloudDirectory]:
        parent_id = str(parent_id or "0")
        parent_path = self._directory_paths.get(parent_id, "/")
        
        # 1. 优先尝试通过 files.manager 按 CID 列目录
        checked, items = self.files.manager.list_files_by_cid_checked(parent_id)
        
        # 2. 如果 CID 失败或为空且在根目录，尝试通过 service.list_directories 路径解析
        if not checked:
            try:
                raw_dirs = self.files.manager.list_directories(parent_path)
                result = []
                for d in raw_dirs:
                    d_id = str(d.get("cid") or d.get("id") or "")
                    d_name = str(d.get("name") or "")
                    d_path = str(d.get("path") or posixpath.join(parent_path, d_name))
                    self._directory_paths[d_id] = d_path
                    result.append(CloudDirectory(d_id, d_name, d_path, True))
                return result
            except Exception as e:
                raise RuntimeError(f"列出115目录失败：{parent_path}，{e}") from e

        result = []
        for item in items:
            is_dir = bool(
                item.get("is_dir")
                or (str(item.get("fid") or "0") == "0" and item.get("cid"))
                or (item.get("cid") and not item.get("sha1"))
            )
            if not is_dir:
                continue
            directory_id = str(item.get("cid") or item.get("id") or item.get("file_id") or "")
            name = str(item.get("name") or item.get("n") or item.get("file_name") or "")
            path = posixpath.join(parent_path, name)
            self._directory_paths[directory_id] = path
            child_checked, children = self.files.manager.list_files_by_cid_checked(directory_id)
            result.append(
                CloudDirectory(directory_id, name, path, bool(child_checked and children))
            )
        return result

    def list_offline_tasks(self) -> list[dict]:
        try:
            from csx.vendor.drive.p115.offline import OfflineDownloadService

            service = OfflineDownloadService(self.files.manager)
            return service.get_offline_tasks(force=True)
        except Exception:
            return []

    def add_offline_task(self, url: str, parent_id: str = "0") -> dict:
        client = getattr(self.files.manager, "client", None)
        if not client:
            raise RuntimeError("115 client 未初始化")
        payload = {"url[0]": url, "wp_path_id": parent_id or "0"}
        return client.clouddownload_task_add_urls(payload)

    def delete_offline_tasks(self, hashes: list[str]) -> bool:
        try:
            from csx.vendor.drive.p115.offline import OfflineDownloadService

            service = OfflineDownloadService(self.files.manager)
            return bool(service.delete_offline_tasks(hashes))
        except Exception:
            return False
