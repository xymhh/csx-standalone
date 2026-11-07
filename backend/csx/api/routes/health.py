"""健康检查与元信息。"""

from __future__ import annotations

from fastapi import APIRouter

from csx import __version__
from csx.api.envelope import ok

router = APIRouter(tags=["meta"])


@router.get("/meta")
def meta() -> dict:
    return ok({"name": "CloudSubscribeX", "version": __version__})
