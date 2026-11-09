"""TMDB 官方影视元数据与热门推荐客户端。"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import OrderedDict
from typing import Any
from urllib.parse import quote

import requests

from csx.infra.settings import settings

logger = logging.getLogger(__name__)

TMDB_API_BASE = os.getenv("CSX_TMDB_API_BASE", "https://api.themoviedb.org/3").rstrip("/")
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE = "https://image.tmdb.org/t/p/w1280"

CACHE_TTL_SECONDS = 2 * 3600  # 2 小时缓存
CACHE_MAX_SIZE = 256
_cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
_lock = threading.RLock()


def _get_api_key() -> str:
    key = os.getenv("CSX_TMDB_API_KEY", "").strip()
    if not key and hasattr(settings, "tmdb_api_key"):
        key = str(getattr(settings, "tmdb_api_key", "") or "").strip()
    if not key:
        p = settings.data_dir / "tmdb_api_key.txt"
        if p.is_file():
            try:
                key = p.read_text().strip()
            except OSError:
                key = ""
    if not key and os.path.exists("/app/working/.csx_tmdb_key"):
        try:
            with open("/app/working/.csx_tmdb_key") as fp:
                key = fp.read().strip()
        except OSError:
            key = ""
    return key


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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "application/json",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            payload = resp.json()
        else:
            logger.warning("TMDB 请求返回状态码 %d: %s", resp.status_code, url.split("?")[0])
            payload = {}
    except Exception as error:
        logger.warning("请求 TMDB 失败：%s（%s）", url.split("?")[0], error)
        payload = {}

    with _lock:
        if payload:
            _cache[url] = (now + CACHE_TTL_SECONDS, payload)
            _cache.move_to_end(url)
            while len(_cache) > CACHE_MAX_SIZE:
                _cache.popitem(last=False)

    return payload


def format_tmdb_item(item: dict[str, Any]) -> dict[str, Any]:
    poster = item.get("poster_path")
    backdrop = item.get("backdrop_path")
    title = item.get("title") or item.get("name") or "未命名"
    media_type = item.get("media_type")
    if not media_type:
        media_type = "tv" if "first_air_date" in item or "name" in item else "movie"

    release_date = item.get("release_date") or item.get("first_air_date") or ""
    year = (
        int(release_date[:4])
        if release_date and len(release_date) >= 4 and release_date[:4].isdigit()
        else None
    )

    genre_ids = item.get("genre_ids")
    if not genre_ids:
        genre_ids = [
            entry.get("id")
            for entry in (item.get("genres") or [])
            if isinstance(entry, dict) and entry.get("id")
        ]

    return {
        "id": item.get("id"),
        "title": title,
        "type": media_type,
        "year": year,
        "release_date": release_date,
        "genre_ids": [int(value) for value in (genre_ids or []) if value],
        "original_language": item.get("original_language") or "",
        "origin_country": list(item.get("origin_country") or []),
        "production_countries": list(item.get("production_countries") or []),
        "vote_average": round(float(item.get("vote_average") or 0.0), 1),
        "overview": item.get("overview") or "",
        "poster_url": f"{TMDB_IMAGE_BASE}{poster}" if poster else None,
        "backdrop_url": f"{TMDB_BACKDROP_BASE}{backdrop}" if backdrop else None,
        "popularity": item.get("popularity", 0),
    }


class TmdbClient:
    """TMDB 元数据与热播推荐封装。"""

    @classmethod
    def diagnose(cls) -> dict[str, Any]:
        key = _get_api_key()
        if not key:
            return {"configured": False, "valid": False, "message": "未配置 TMDB API Key"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept": "application/json",
        }
        url = f"{TMDB_API_BASE}/configuration?api_key={key}"
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                return {
                    "configured": True,
                    "valid": True,
                    "message": "连通正常",
                    "key_prefix": f"{key[:6]}...",
                }
            return {
                "configured": True,
                "valid": False,
                "message": f"TMDB 接口返回错误码 {resp.status_code}: {resp.text[:100]}",
                "key_prefix": f"{key[:6]}...",
            }
        except Exception as error:
            return {
                "configured": True,
                "valid": False,
                "message": f"连接异常: {type(error).__name__} {error}",
                "key_prefix": f"{key[:6]}...",
            }

    @classmethod
    def get_trending(cls) -> list[dict[str, Any]]:
        key = _get_api_key()
        if not key:
            return []
        url = f"{TMDB_API_BASE}/trending/all/day?api_key={key}&language=zh-CN"
        data = _cached_fetch(url)
        results = data.get("results") or []
        return [format_tmdb_item(item) for item in results if item.get("id")]

    @classmethod
    def get_popular_tv(cls) -> list[dict[str, Any]]:
        key = _get_api_key()
        if not key:
            return []
        url = f"{TMDB_API_BASE}/tv/popular?api_key={key}&language=zh-CN&page=1"
        data = _cached_fetch(url)
        results = data.get("results") or []
        for item in results:
            item["media_type"] = "tv"
        return [format_tmdb_item(item) for item in results if item.get("id")]

    @classmethod
    def get_popular_movies(cls) -> list[dict[str, Any]]:
        key = _get_api_key()
        if not key:
            return []
        url = f"{TMDB_API_BASE}/movie/popular?api_key={key}&language=zh-CN&page=1"
        data = _cached_fetch(url)
        results = data.get("results") or []
        for item in results:
            item["media_type"] = "movie"
        return [format_tmdb_item(item) for item in results if item.get("id")]

    @classmethod
    def search(cls, query: str) -> list[dict[str, Any]]:
        key = _get_api_key()
        query = str(query or "").strip()
        if not key or not query:
            return []
        url = (
            f"{TMDB_API_BASE}/search/multi?api_key={key}&language=zh-CN&query={quote(query)}&page=1"
        )
        data = _cached_fetch(url)
        results = data.get("results") or []
        return [
            format_tmdb_item(item)
            for item in results
            if item.get("id") and item.get("media_type") in {"tv", "movie"}
        ]

    @classmethod
    def get_detail(cls, media_type: str, tmdb_id: int) -> dict[str, Any] | None:
        key = _get_api_key()
        if not key or not tmdb_id:
            return None
        m_type = "tv" if media_type == "tv" else "movie"
        url = f"{TMDB_API_BASE}/{m_type}/{tmdb_id}?api_key={key}&language=zh-CN"
        try:
            data = _cached_fetch(url)
            if not data or not data.get("id"):
                return None
            res = format_tmdb_item(data)
            if m_type == "tv":
                seasons = []
                for s in data.get("seasons") or []:
                    s_num = s.get("season_number", 0)
                    if s_num > 0:
                        seasons.append(
                            {
                                "season_number": s_num,
                                "name": s.get("name") or f"第 {s_num} 季",
                                "episode_count": s.get("episode_count", 12),
                                "poster_url": f"{TMDB_IMAGE_BASE}{s.get('poster_path')}"
                                if s.get("poster_path")
                                else None,
                            }
                        )
                res["seasons"] = seasons
            return res
        except Exception as error:
            logger.warning("解析 TMDB %s/%s 详情失败: %s", m_type, tmdb_id, error)
            return None
