"""进程内 TTL 缓存。

平台缓存（`create_platform_ttl_cache`）会把值序列化后落库，读取时反序列化；
对「字典列表」这类结构它并不能保证原样返回（实测拿到的是字符串列表），
分享状态/文件列表这类必须保持原始结构的缓存因此改用纯内存实现。
"""

from __future__ import annotations

import threading
import time
from typing import Any, Iterator


class InMemoryTTLCache:
    """最小可用的线程安全 TTL 缓存，值保持原对象结构。"""

    def __init__(self, maxsize: int = 500, ttl: int = 1800) -> None:
        self._data: dict[Any, tuple[Any, float]] = {}
        self._maxsize = max(1, int(maxsize))
        self._ttl = max(1, int(ttl))
        self._lock = threading.RLock()

    def _alive(self, key: Any) -> bool:
        item = self._data.get(key)
        if item is None:
            return False
        if item[1] < time.time():
            self._data.pop(key, None)
            return False
        return True

    def __contains__(self, key: Any) -> bool:
        return self._alive(key)

    def __getitem__(self, key: Any) -> Any:
        if not self._alive(key):
            raise KeyError(key)
        return self._data[key][0]

    def __setitem__(self, key: Any, value: Any) -> None:
        with self._lock:
            if len(self._data) >= self._maxsize:
                self._data.clear()
            self._data[key] = (value, time.time() + self._ttl)

    def __delitem__(self, key: Any) -> None:
        self._data.pop(key, None)

    def __iter__(self) -> Iterator[Any]:
        return iter(list(self._data.keys()))

    def __len__(self) -> int:
        return len(self._data)

    def keys(self) -> list[Any]:
        return list(self._data.keys())

    def get(self, key: Any, default: Any = None, **kwargs: Any) -> Any:
        return self._data[key][0] if self._alive(key) else default

    def set(self, key: Any, value: Any, **kwargs: Any) -> None:
        self[key] = value

    def delete(self, key: Any, **kwargs: Any) -> None:
        self._data.pop(key, None)

    def exists(self, key: Any, **kwargs: Any) -> bool:
        return self._alive(key)

    def pop(self, key: Any, default: Any = None, **kwargs: Any) -> Any:
        if not self._alive(key):
            return default
        return self._data.pop(key)[0]

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
