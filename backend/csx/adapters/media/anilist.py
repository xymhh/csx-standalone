"""AniList 本季热门新番客户端。"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from datetime import datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)

ANILIST_GRAPHQL_URL = "https://graphql.anilist.co"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

SEASON_QUERY = """
query($season:MediaSeason,$year:Int){
  Page(page:1,perPage:50){
    media(type:ANIME,season:$season,seasonYear:$year,sort:POPULARITY_DESC){
      id
      title{romaji native}
      coverImage{extraLarge}
      averageScore
      seasonYear
      format
    }
  }
}
"""

CACHE_TTL_SECONDS = 2 * 3600
CACHE_MAX_SIZE = 16
_cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
_lock = threading.RLock()


def season_for_month(month: int) -> str:
    """按月份推算 AniList 季度。"""
    if month in (12, 1, 2):
        return "WINTER"
    if 3 <= month <= 5:
        return "SPRING"
    if 6 <= month <= 8:
        return "SUMMER"
    return "FALL"


def _cached_fetch(cache_key: str, variables: dict[str, Any]) -> dict[str, Any]:
    now = time.monotonic()
    with _lock:
        if cache_key in _cache:
            exp, data = _cache[cache_key]
            if exp > now:
                _cache.move_to_end(cache_key)
                return data
            del _cache[cache_key]

    headers = {
        "User-Agent": BROWSER_UA,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {}
    try:
        resp = requests.post(
            ANILIST_GRAPHQL_URL,
            headers=headers,
            json={"query": SEASON_QUERY, "variables": variables},
            timeout=12,
        )
        if resp.status_code == 200:
            payload = resp.json()
        else:
            logger.warning("AniList 请求返回状态码 %d", resp.status_code)
    except Exception as error:
        logger.warning("请求 AniList 失败：%s", error)

    with _lock:
        if payload:
            _cache[cache_key] = (now + CACHE_TTL_SECONDS, payload)
            _cache.move_to_end(cache_key)
            while len(_cache) > CACHE_MAX_SIZE:
                _cache.popitem(last=False)

    return payload


def _format_item(item: dict[str, Any]) -> dict[str, Any] | None:
    raw_id = item.get("id")
    if raw_id is None:
        return None
    try:
        anilist_id = int(raw_id)
    except (TypeError, ValueError):
        return None

    title = item.get("title") if isinstance(item.get("title"), dict) else {}
    cover = item.get("coverImage") if isinstance(item.get("coverImage"), dict) else {}
    try:
        score = float(item.get("averageScore") or 0) / 10
    except (TypeError, ValueError):
        score = 0.0

    return {
        "id": -anilist_id,
        "title": title.get("native") or title.get("romaji") or "未命名",
        "type": "tv",
        "year": item.get("seasonYear"),
        "release_date": "",
        "vote_average": round(score, 1),
        "overview": "",
        "poster_url": cover.get("extraLarge") or None,
        "backdrop_url": None,
    }


def get_season(month: int | None = None) -> list[dict[str, Any]]:
    """获取当前（或指定月份对应）季度的热门新番。"""
    now = datetime.now()
    current_month = month if month is not None else now.month
    season = season_for_month(current_month)
    year = now.year
    cache_key = f"anilist:{season}:{year}"
    data = _cached_fetch(cache_key, {"season": season, "year": year})
    page = data.get("data", {}).get("Page") if isinstance(data, dict) else {}
    media = (page or {}).get("media") or []
    result: list[dict[str, Any]] = []
    for entry in media:
        if not isinstance(entry, dict):
            continue
        formatted = _format_item(entry)
        if formatted is not None:
            result.append(formatted)
    return result
