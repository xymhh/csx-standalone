"""豆瓣正在热映 / 热门影视榜单客户端。"""

from __future__ import annotations

import logging
import re
import threading
import time
from collections import OrderedDict
from typing import Any

from curl_cffi import requests

logger = logging.getLogger(__name__)

DOUBAN_API_BASE = "https://movie.douban.com/j/search_subjects"
DOUBAN_NOWPLAYING_URL = "https://movie.douban.com/cinema/nowplaying/"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

CACHE_TTL_SECONDS = 2 * 3600
CACHE_MAX_SIZE = 128
_cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
_lock = threading.RLock()

# 每个榜单给出 tag 回退链：豆瓣会周期性清空个别 tag，空结果自动降级
_RANK_CONFIG = {
    "showing": ("movie", ("正在热映", "热映", "热门"), "movie"),
    "movie_hot": ("movie", ("热门",), "movie"),
    "tv_hot": ("tv", ("热门", "最近热门剧集"), "tv"),
}

_YEAR_RE = re.compile(r"(?:19|20)\d{2}")
_NOWPLAYING_BLOCK_RE = re.compile(r'<li\s+id="(\d+)"\s+class="list-item"(.*?)</li>', re.S)
_NOWPLAYING_IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.S)


def _parse_year(title: str) -> int | None:
    match = _YEAR_RE.search(title or "")
    return int(match.group()) if match else None


def _cached_fetch(url: str) -> dict[str, Any]:
    now = time.monotonic()
    with _lock:
        if url in _cache:
            exp, data = _cache[url]
            if exp > now:
                _cache.move_to_end(url)
                return data
            del _cache[url]

    headers = {
        "User-Agent": BROWSER_UA,
        "Accept": "application/json",
        "Referer": "https://movie.douban.com/",
    }
    try:
        resp = requests.get(url, headers=headers, impersonate="chrome", timeout=12)
        if resp.status_code == 200:
            payload = resp.json()
        else:
            logger.warning("豆瓣请求返回状态码 %d: %s", resp.status_code, url.split("?")[0])
            payload = {}
    except Exception as error:
        logger.warning("请求豆瓣失败：%s（%s）", url.split("?")[0], error)
        payload = {}

    with _lock:
        if payload:
            _cache[url] = (now + CACHE_TTL_SECONDS, payload)
            _cache.move_to_end(url)
            while len(_cache) > CACHE_MAX_SIZE:
                _cache.popitem(last=False)

    return payload


def _cached_text(url: str) -> str:
    """Fetch an HTML page with the same TTL cache used for JSON endpoints."""
    now = time.monotonic()
    with _lock:
        if url in _cache:
            exp, data = _cache[url]
            if exp > now:
                _cache.move_to_end(url)
                return str(data)
            del _cache[url]

    headers = {
        "User-Agent": BROWSER_UA,
        "Accept": "text/html,application/xhtml+xml",
        "Referer": "https://movie.douban.com/",
    }
    text = ""
    try:
        resp = requests.get(url, headers=headers, impersonate="chrome", timeout=15)
        if resp.status_code == 200:
            text = resp.text
        else:
            logger.warning("豆瓣页面返回状态码 %d", resp.status_code)
    except Exception as error:
        logger.warning("请求豆瓣正在上映失败：%s", error)

    with _lock:
        if text:
            _cache[url] = (now + CACHE_TTL_SECONDS, text)
            _cache.move_to_end(url)
            while len(_cache) > CACHE_MAX_SIZE:
                _cache.popitem(last=False)
    return text


def _attr(block: str, name: str) -> str:
    match = re.search(rf'{name}="([^"]*)"', block)
    return match.group(1) if match else ""


def _nowplaying_items(limit: int = 50) -> list[dict[str, Any]]:
    html = _cached_text(DOUBAN_NOWPLAYING_URL)
    if not html:
        return []
    seen: set[int] = set()
    result: list[dict[str, Any]] = []
    for raw_id, block in _NOWPLAYING_BLOCK_RE.findall(html):
        try:
            douban_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if douban_id in seen:
            continue
        seen.add(douban_id)
        title = _attr(block, "data-title").strip()
        if not title:
            continue
        try:
            score = float(_attr(block, "data-score") or 0)
        except ValueError:
            score = 0.0
        release = _attr(block, "data-release")
        year = int(release) if release.isdigit() else _parse_year(title)
        img = _NOWPLAYING_IMG_RE.search(block)
        result.append(
            {
                "id": -douban_id,
                "title": title,
                "type": "movie",
                "year": year,
                "release_date": "",
                "vote_average": round(score, 1),
                "overview": "",
                "poster_url": img.group(1) if img else None,
                "backdrop_url": None,
            }
        )
        if len(result) >= limit:
            break
    return result


def _format_item(item: dict[str, Any], media_type: str) -> dict[str, Any] | None:
    raw_id = item.get("id")
    if raw_id is None:
        return None
    try:
        douban_id = int(raw_id)
    except (TypeError, ValueError):
        return None

    title = str(item.get("title") or "").strip()
    try:
        rate = float(item.get("rate") or 0)
    except (TypeError, ValueError):
        rate = 0.0

    return {
        "id": -douban_id,
        "title": title or "未命名",
        "type": media_type,
        "year": _parse_year(title),
        "release_date": "",
        "vote_average": round(rate, 1),
        "overview": "",
        "poster_url": item.get("cover") or None,
        "backdrop_url": None,
    }


def get_rank(rank: str) -> list[dict[str, Any]]:
    """获取豆瓣榜单：showing / movie_hot / tv_hot。"""
    config = _RANK_CONFIG.get(rank)
    if config is None:
        return []
    if rank == "showing":
        items = _nowplaying_items()
        if items:
            return items

    source_type, tags, media_type = config
    subjects: list[dict[str, Any]] = []
    for tag in tags:
        url = f"{DOUBAN_API_BASE}?type={source_type}&tag={tag}&page_limit=50&page_start=0"
        subjects = _cached_fetch(url).get("subjects") or []
        if subjects:
            break
    result: list[dict[str, Any]] = []
    for subject in subjects:
        formatted = _format_item(subject, media_type)
        if formatted is not None:
            result.append(formatted)
    return result
