"""登录失败限流（进程内，单用户场景足够）。"""

from __future__ import annotations

import time
from collections import defaultdict

from csx.infra.settings import settings

_attempts: dict[str, list[float]] = defaultdict(list)


def _prune(key: str, now: float) -> None:
    window = settings.login_window_seconds
    _attempts[key] = [t for t in _attempts[key] if now - t < window]


def is_blocked(key: str) -> bool:
    now = time.monotonic()
    _prune(key, now)
    return len(_attempts[key]) >= settings.login_max_attempts


def record_failure(key: str) -> None:
    now = time.monotonic()
    _prune(key, now)
    _attempts[key].append(now)


def reset(key: str) -> None:
    _attempts.pop(key, None)
