"""Bangumi 每日放送日历客户端。"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from typing import Any

import requests

logger = logging.getLogger(__name__)

BANGUMI_CALENDAR_URL = "https://api.bgm.tv/calendar"
BANGUMI_UA = "csx-standalone/0.1 (https://github.com/xymhh/csx-standalone)"

CACHE_TTL_SECONDS = 2 * 3600
CACHE_MAX_SIZE = 32
_cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
_lock = threading.RLock()


def _cached_fetch(url: str) -> list[dict[str, Any]]:
    now = time.monotonic()
    with _lock:
        if url in _cache:
            exp, data = _cache[url]
            if exp > now:
                _cache.move_to_end(url)
                return data
            del _cache[url]

    headers = {
        "User-Agent": BANGUMI_UA,
        "Accept": "application/json",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            payload = resp.json()
        else:
            logger.warning("Bangumi 请求返回状态码 %d: %s", resp.status_code, url.split("?")[0])
            payload = []
    except Exception as error:
        logger.warning("请求 Bangumi 失败：%s（%s）", url.split("?")[0], error)
        payload = []

    with _lock:
        if payload:
            _cache[url] = (now + CACHE_TTL_SECONDS, payload)
            _cache.move_to_end(url)
            while len(_cache) > CACHE_MAX_SIZE:
                _cache.popitem(last=False)

    return payload


def _parse_year(value: Any) -> int | None:
    text = str(value or "")
    return int(text[:4]) if len(text) >= 4 and text[:4].isdigit() else None


def _format_item(item: dict[str, Any]) -> dict[str, Any] | None:
    raw_id = item.get("id")
    if raw_id is None:
        return None
    try:
        bgm_id = int(raw_id)
    except (TypeError, ValueError):
        return None

    rating = item.get("rating") if isinstance(item.get("rating"), dict) else {}
    try:
        score = float(rating.get("score") or 0)
    except (TypeError, ValueError):
        score = 0.0

    images = item.get("images") if isinstance(item.get("images"), dict) else {}
    summary = str(item.get("summary") or "")
    air_date = item.get("air_date")

    return {
        "id": -bgm_id,
        "title": item.get("name_cn") or item.get("name") or "未命名",
        "type": "tv",
        "year": _parse_year(air_date),
        "release_date": "",
        "vote_average": round(score, 1),
        "overview": summary[:200],
        "poster_url": images.get("large") or None,
        "backdrop_url": None,
    }


def get_calendar() -> list[dict[str, Any]]:
    """合并 7 天每日放送，去重后按评分降序取前 60 条。"""
    days = _cached_fetch(BANGUMI_CALENDAR_URL)
    if not isinstance(days, list):
        return []

    seen: set[int] = set()
    items: list[dict[str, Any]] = []
    for day in days:
        if not isinstance(day, dict):
            continue
        for raw in day.get("items") or []:
            if not isinstance(raw, dict):
                continue
            formatted = _format_item(raw)
            if formatted is None:
                continue
            item_id = formatted["id"]
            if item_id in seen:
                continue
            seen.add(item_id)
            items.append(formatted)

    items.sort(key=lambda entry: entry.get("vote_average") or 0, reverse=True)
    return items[:60]
