"""FastAPI 应用入口。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from csx import __version__
from csx.api.deps import COOKIE_NAME
from csx.api.envelope import ok
from csx.api.routes import auth, health
from csx.application.auth import session_user
from csx.infra.bootstrap import ensure_admin, init_db
from csx.infra.db import SessionLocal
from csx.infra.logging import setup_logging
from csx.infra.settings import settings

PUBLIC_API_PATHS = {"/api/v1/auth/login"}


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.log_level)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    ensure_admin()
    yield


app = FastAPI(title="CloudSubscribeX", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _lookup_user(token: str) -> bool:
    if not token:
        return False
    with SessionLocal() as db:
        return session_user(db, token) is not None


@app.middleware("http")
async def auth_guard(request: Request, call_next: Any) -> Any:
    path = request.url.path
    if not path.startswith("/api/") or path in PUBLIC_API_PATHS:
        return await call_next(request)
    token = request.cookies.get(COOKIE_NAME, "")
    if not await run_in_threadpool(_lookup_user, token):
        return JSONResponse(
            status_code=401,
            content={
                "ok": False,
                "data": None,
                "error": {"code": "UNAUTHORIZED", "message": "需要登录", "hint": None},
            },
        )
    return await call_next(request)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        error = {
            "code": detail.get("code", "ERROR"),
            "message": detail.get("message", "请求失败"),
            "hint": detail.get("hint"),
        }
    else:
        error = {"code": "ERROR", "message": str(detail), "hint": None}
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "data": None, "error": error},
        headers=getattr(exc, "headers", None),
    )


app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
def health_root() -> dict:
    return ok({"status": "up", "version": __version__})


class SPAStaticFiles(StaticFiles):
    """前端用 history 路由，未知路径回退到 index.html。"""

    async def get_response(self, path: str, scope: Any) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


if settings.web_dist.is_dir():
    app.mount("/", SPAStaticFiles(directory=settings.web_dist, html=True), name="web")
