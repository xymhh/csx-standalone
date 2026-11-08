"""TMDB 官方推荐与搜索路由。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from csx.adapters.media.tmdb import TmdbClient
from csx.api.envelope import ok

router = APIRouter(prefix="/tmdb", tags=["tmdb"])


@router.get("/trending")
def get_trending():
    """获取今日全网热搜/热播流。"""
    items = TmdbClient.get_trending()
    return ok(items)


@router.get("/popular/tv")
def get_popular_tv():
    """获取热门电视剧榜单。"""
    items = TmdbClient.get_popular_tv()
    return ok(items)


@router.get("/popular/movies")
def get_popular_movies():
    """获取热门电影榜单。"""
    items = TmdbClient.get_popular_movies()
    return ok(items)


@router.get("/search")
def search_tmdb(query: str = Query(min_length=1, max_length=128)):
    """按标题搜索 TMDB 影视。"""
    items = TmdbClient.search(query)
    return ok(items)


@router.get("/detail/{media_type}/{tmdb_id}")
def get_tmdb_detail(media_type: str, tmdb_id: int):
    """获取指定影视完整季集详情。"""
    if media_type not in {"tv", "movie"}:
        raise HTTPException(
            400, detail={"code": "INVALID_TYPE", "message": "类型只能为 tv 或 movie"}
        )
    detail = TmdbClient.get_detail(media_type, tmdb_id)
    if detail is None:
        raise HTTPException(
            404, detail={"code": "TMDB_NOT_FOUND", "message": "未找到对应的 TMDB 影视信息"}
        )
    return ok(detail)
