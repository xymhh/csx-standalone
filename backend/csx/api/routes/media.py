"""外链海报代理。

豆瓣与 Bangumi 的图床带 Referer 校验，浏览器从本站直连会被拒绝（豆瓣返回 418），
因此统一由服务端按来源补 Referer 后转发，并在浏览器侧缓存一周。
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from curl_cffi import requests
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["media"])

# host 后缀白名单：只代理明确需要的图床，避免变成任意 URL 代理
_ALLOWED_HOSTS = ("doubanio.com", "bgm.tv", "anilist.co", "tmdb.org")

_REFERERS = {
    "doubanio.com": "https://movie.douban.com/",
    "bgm.tv": "https://bgm.tv/",
    "anilist.co": "https://anilist.co/",
    "tmdb.org": "https://www.themoviedb.org/",
}

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


@router.get("/poster")
def proxy_poster(url: str = Query(min_length=8, max_length=1024)):
    """按白名单转发图床图片，返回原始字节。"""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not any(host.endswith(suffix) for suffix in _ALLOWED_HOSTS):
        raise HTTPException(
            400,
            detail={
                "code": "POSTER_HOST_NOT_ALLOWED",
                "message": "该图片地址不在允许的图床白名单内",
            },
        )

    referer = next(
        (value for suffix, value in _REFERERS.items() if host.endswith(suffix)),
        f"https://{host}/",
    )
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": _UA, "Referer": referer, "Accept": "image/*"},
            impersonate="chrome",
            timeout=15,
        )
    except Exception as error:
        logger.warning("海报代理请求失败：%s", type(error).__name__)
        raise HTTPException(
            404, detail={"code": "POSTER_FETCH_FAILED", "message": "图片拉取失败"}
        ) from error

    if resp.status_code != 200 or not resp.content:
        logger.warning("海报代理返回 %d：%s", resp.status_code, host)
        raise HTTPException(404, detail={"code": "POSTER_NOT_FOUND", "message": "图片不可用"})

    return Response(
        content=resp.content,
        media_type=resp.headers.get("content-type", "image/jpeg"),
        headers={"Cache-Control": "public, max-age=604800"},
    )
