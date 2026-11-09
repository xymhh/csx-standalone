"""跨盘中继适配器：封装 vendor 的 ``CrossTransferTaskManager``。

资源盘与目标盘不同时，把源盘上的文件经本地缓存下载后秒传/上传到目标盘。
所有 ``csx.vendor`` 接触点都收在这一层。
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MIN_FREE_BYTES = 512 * 1024 * 1024


class CrossRelay:
    """一个实例复用一个任务管理器（含并发槽、断点续传与缓存引用计数）。"""

    def __init__(
        self,
        providers: dict[str, Any],
        cache_dir: str,
        download_threads: int = 5,
        max_concurrent: int = 2,
        direct_stream: bool = True,
        on_change: Any = None,
    ) -> None:
        from csx.vendor.core.transfer import CrossTransferTaskManager

        self._providers = providers
        self.cache_dir = Path(cache_dir)
        self._manager = CrossTransferTaskManager(
            provider_resolver=self._provider,
            download_path=str(self.cache_dir),
            download_threads=download_threads,
            max_concurrent=max_concurrent,
            direct_stream=direct_stream,
            rapid_miss_action="abort",
            on_change=on_change,
        )

    def _provider(self, key: str) -> Any:
        provider = self._providers.get(str(key or "").lower())
        if provider is None:
            raise RuntimeError(f"未配置 {key} 网盘账号，无法跨盘转存")
        return provider

    def supports(self, provider: str) -> bool:
        return str(provider or "").lower() in self._providers

    def free_bytes(self) -> int:
        try:
            return int(shutil.disk_usage(self.cache_dir).free)
        except OSError:
            return 0

    def relay(
        self,
        source_key: str,
        source_dir: str,
        file_name: str,
        target_key: str,
        target_dir: str,
        target_name: str = "",
        parent_task_id: str = "",
    ) -> dict[str, Any]:
        """把一个已在源盘 inbox 的文件中继到目标盘，返回目标盘文件信息。"""
        from csx.vendor.core.cloud import CloudDriveCapability

        source_provider = self._provider(source_key)
        target_provider = self._provider(target_key)
        query = source_provider.require(CloudDriveCapability.FILE_QUERY)
        source_file = query.find_file(source_dir, file_name)
        if source_file is None:
            raise RuntimeError(f"源盘 {source_key} 中找不到中转文件：{file_name}")
        size = int(getattr(source_file, "size", 0) or 0)
        required = max(MIN_FREE_BYTES, int(size * 1.1))
        free = self.free_bytes()
        if free and free < required:
            raise RuntimeError(
                f"本地缓存空间不足：剩余 {free // (1024 * 1024)}MB，"
                f"至少需要 {required // (1024 * 1024)}MB"
            )
        task = self._manager.create_from_cloud_file(
            source_key=source_key,
            source_file=source_file,
            target_key=target_key,
            save_path=target_dir,
            target_name=target_name or file_name,
            parent_task_id=parent_task_id,
        )
        task_id = str(task.get("id") or "")
        ok = self._manager.wait(task_id, poll_seconds=1.0)
        finished = next(
            (item for item in self._manager.list() if str(item.get("id")) == task_id),
            {},
        )
        if not ok:
            error = str(finished.get("error") or finished.get("message") or "跨盘中继失败")
            raise RuntimeError(f"{file_name} 跨盘转存失败：{error}")
        resolved_name = str(finished.get("result_file_name") or target_name or file_name)
        file_id = str(finished.get("result_file_id") or "")
        if not file_id:
            found = target_provider.require(CloudDriveCapability.FILE_QUERY).find_file(
                target_dir, resolved_name
            )
            if found is None:
                raise RuntimeError(f"{file_name} 上传后未在 {target_key} 找到文件")
            return {
                "file_id": str(found.id or ""),
                "path": f"{target_dir.rstrip('/')}/{found.name}",
                "size": int(found.size or 0),
                "sha1": str(found.sha1 or ""),
                "method": str(finished.get("method") or "fallback"),
                "file": found,
            }
        landed = target_provider.require(CloudDriveCapability.FILE_QUERY).find_file(
            target_dir, resolved_name
        )
        return {
            "file_id": file_id,
            "path": f"{target_dir.rstrip('/')}/{resolved_name}",
            "size": int(finished.get("result_file_size") or 0),
            "sha1": str(finished.get("result_sha1") or ""),
            "method": str(finished.get("method") or "fallback"),
            "file": landed,
        }

    def cleanup_cache(self) -> int:
        """清理缓存目录下残留的中继文件（只删文件，不动目录本身）。"""
        removed = 0
        for path in self.cache_dir.rglob("*"):
            if not path.is_file():
                continue
            try:
                path.unlink()
                removed += 1
            except OSError:
                continue
        return removed
