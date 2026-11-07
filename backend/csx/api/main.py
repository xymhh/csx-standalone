"""FastAPI 应用入口。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from csx import __version__
from csx.api.envelope import ok
from csx.api.routes import health
from csx.infra.logging import setup_logging
from csx.infra.settings import settings


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.log_level)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="CloudSubscribeX", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")


@app.get("/health", tags=["meta"])
def health_root() -> dict:
    return ok({"status": "up", "version": __version__})


if settings.web_dist.is_dir():
    app.mount("/", StaticFiles(directory=settings.web_dist, html=True), name="web")
