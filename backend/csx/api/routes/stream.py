"""Public 302 redirects to short-lived provider download URLs."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from csx.infra.db import get_db
from csx.infra.drive_runtime import drive_for
from csx.infra.models import LibraryFile

router = APIRouter(prefix="/stream", tags=["stream"])
CACHE_TTL_SECONDS = 45 * 60
CACHE_MAX_ENTRIES = 512
_cache: OrderedDict[tuple[int, str], tuple[float, str]] = OrderedDict()
_cache_lock = threading.RLock()


def _cached_url(file_id: int, user_agent: str, now: float | None = None) -> str | None:
    key = (file_id, user_agent)
    current = time.monotonic() if now is None else now
    with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        expires_at, url = entry
        if expires_at <= current:
            del _cache[key]
            return None
        _cache.move_to_end(key)
        return url


def _remember_url(file_id: int, user_agent: str, url: str, now: float | None = None) -> None:
    current = time.monotonic() if now is None else now
    key = (file_id, user_agent)
    with _cache_lock:
        _cache[key] = (current + CACHE_TTL_SECONDS, url)
        _cache.move_to_end(key)
        while len(_cache) > CACHE_MAX_ENTRIES:
            _cache.popitem(last=False)


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


@router.get("/redirect", include_in_schema=False)
def stream_redirect(
    request: Request,
    file_id: int = Query(gt=0),
    token: str | None = None,
    db: Session = Depends(get_db),
):
    del token  # Endpoint is intentionally public for media players that cannot send cookies.
    row = db.get(LibraryFile, file_id)
    if row is None:
        raise HTTPException(
            404, detail={"code": "LIBRARY_FILE_NOT_FOUND", "message": "媒体文件不存在"}
        )
    provider = str(row.provider or "").strip().lower()
    if provider not in {"115", "quark"}:
        raise HTTPException(
            409, detail={"code": "DRIVE_PROVIDER_MISSING", "message": "文件未关联受支持的网盘账号"}
        )
    user_agent = request.headers.get("user-agent", "")
    url = _cached_url(row.id, user_agent)
    if url is None:
        drive = drive_for(db, provider, getattr(request.app.state, "drives", {}))
        if drive is None:
            raise HTTPException(
                404, detail={"code": "ACCOUNT_NOT_FOUND", "message": "网盘账号尚未绑定"}
            )
        try:
            resolver = getattr(drive, "resolve_download_link", None) or drive.get_download_url
            url = str(resolver(row.path))
        except Exception as error:
            raise HTTPException(
                502,
                detail={"code": "DOWNLOAD_LINK_FAILED", "message": str(error)},
            ) from error
        _remember_url(row.id, user_agent, url)
    return RedirectResponse(url=url, status_code=302)
