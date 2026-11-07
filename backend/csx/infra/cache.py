"""Small thread-safe TTL cache used by vendored adapters."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any


class TTLCache:
    """Bounded in-memory cache with per-entry expiration."""

    def __init__(
        self,
        region: str = "",
        *,
        maxsize: int = 256,
        ttl: float = 300,
        **_: Any,
    ) -> None:
        self.region = region
        self.maxsize = max(1, int(maxsize))
        self.ttl = max(0.0, float(ttl))
        self._entries: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.RLock()

    def _purge(self, key: str | None = None) -> None:
        now = time.monotonic()
        expired = [
            entry_key
            for entry_key, (expires, _) in self._entries.items()
            if expires <= now or entry_key == key
        ]
        for entry_key in expired:
            self._entries.pop(entry_key, None)

    def __len__(self) -> int:
        with self._lock:
            self._purge()
            return len(self._entries)

    def __contains__(self, key: object) -> bool:
        return self.get(str(key)) is not None

    def __getitem__(self, key: str) -> Any:
        with self._lock:
            self._purge()
            try:
                _, value = self._entries[key]
            except KeyError:
                raise KeyError(key) from None
            self._entries.move_to_end(key)
            return value

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        with self._lock:
            self._purge()
            try:
                del self._entries[key]
            except KeyError:
                raise KeyError(key) from None

    def get(self, key: str, default: Any = None, **_: Any) -> Any:
        with self._lock:
            self._purge()
            entry = self._entries.get(key)
            if entry is None:
                return default
            self._entries.move_to_end(key)
            return entry[1]

    def set(self, key: str, value: Any, *, ttl: float | None = None, **_: Any) -> None:
        with self._lock:
            self._purge(key)
            lifetime = self.ttl if ttl is None else max(0.0, float(ttl))
            if lifetime == 0:
                return
            self._entries[key] = (time.monotonic() + lifetime, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.maxsize:
                self._entries.popitem(last=False)

    def delete(self, key: str, **_: Any) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def exists(self, key: str, **_: Any) -> bool:
        with self._lock:
            self._purge()
            return key in self._entries

    def pop(self, key: str, default: Any = None, **_: Any) -> Any:
        with self._lock:
            self._purge()
            entry = self._entries.pop(key, None)
            return default if entry is None else entry[1]

    def setdefault(self, key: str, default: Any = None, **kwargs: Any) -> Any:
        current = self.get(key)
        if current is not None:
            return current
        self.set(key, default, **kwargs)
        return default

    def update(self, other: Any, **kwargs: Any) -> None:
        for key, value in dict(other or {}).items():
            self.set(key, value, **kwargs)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
