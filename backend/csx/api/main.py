"""FastAPI 应用入口。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from csx import __version__
from csx.api.deps import COOKIE_NAME
from csx.api.envelope import fail, ok
from csx.api.routes import auth, health, p6, resources, system
from csx.application.auth import session_user
from csx.infra.bootstrap import ensure_admin, init_db
from csx.infra.checkin_runtime import scheduled_checkin
from csx.infra.db import SessionLocal
from csx.infra.drive_runtime import configured_drives
from csx.infra.logging import setup_logging
from csx.infra.scheduler import TaskScheduler
from csx.infra.settings import settings

PUBLIC_API_PATHS = {"/api/v1/auth/login"}


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.log_level)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    ensure_admin()
    with SessionLocal() as db:
        app.state.drives = configured_drives(db)
    scheduler = TaskScheduler(
        drives=app.state.drives,
        checkin_callback=lambda: scheduled_checkin(SessionLocal),
    )
    app.state.scheduler = scheduler
    await scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()


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
            content=fail("UNAUTHORIZED", "需要登录"),
        )
    return await call_next(request)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        error = fail(
            detail.get("code", "ERROR"),
            detail.get("message", "请求失败"),
            detail.get("hint"),
        )
    else:
        error = fail("ERROR", str(detail))
    return JSONResponse(
        status_code=exc.status_code,
        content=error,
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=fail("VALIDATION_ERROR", "请求参数无效"),
    )


app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
for resource_router in (
    resources.subscriptions,
    resources.progress,
    resources.candidates,
    resources.tasks,
    resources.history,
    resources.library,
    resources.settings_api,
    resources.accounts,
    resources.doctor,
    resources.events,
):
    app.include_router(resource_router, prefix="/api/v1")
app.include_router(p6.checkin, prefix="/api/v1")
app.include_router(p6.strm, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


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
