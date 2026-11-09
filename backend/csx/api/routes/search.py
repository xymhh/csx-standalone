"""按后台已配置的搜索渠道搜索影视资源。

路由挂在 ``/api/v1/search``，受 ``auth_guard`` 保护。搜索本身只读，不写库、
不消耗积分（需要解锁的渠道只返回「需解锁」，扣点在转存页由用户确认）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from csx.adapters.search import executor
from csx.api.envelope import ok
from csx.infra.db import get_db

router = APIRouter(prefix="/search", tags=["search"])

ALLOWED_LIMITS = {10, 20, 30, 50}
ALLOWED_TYPES = {"all", "movie", "tv"}


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    """后台已注册的搜索渠道与启用状态。"""
    saved = executor.saved_sources(db)
    return ok({"sources": executor.source_catalog(saved)})


@router.get("")
def search(
    q: str = Query("", description="片名关键词"),
    type: str = Query("all"),
    year: int | None = Query(None, ge=1900, le=2100),
    season: int | None = Query(None, ge=0, le=100),
    sources: str = Query("", description="逗号分隔的渠道 id，留空表示全部已启用渠道"),
    limit: int = Query(20),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    keyword = str(q or "").strip()
    if not keyword:
        raise HTTPException(
            status_code=422,
            detail={"code": "EMPTY_QUERY", "message": "请输入要搜索的片名"},
        )
    if len(keyword) > 100:
        raise HTTPException(
            status_code=422,
            detail={"code": "QUERY_TOO_LONG", "message": "关键词请控制在 100 字以内"},
        )
    media_type = str(type or "all").strip().lower()
    if media_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_TYPE", "message": "type 仅支持 all/movie/tv"},
        )
    per_source = 20 if limit not in ALLOWED_LIMITS else limit
    source_ids = [item.strip() for item in str(sources or "").split(",") if item.strip()]
    return ok(
        executor.search_resources(
            db,
            keyword=keyword,
            media_type=media_type,
            year=year,
            season=season,
            source_ids=source_ids,
            limit=per_source,
        )
    )
