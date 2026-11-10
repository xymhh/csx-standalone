"""订阅自动搜源：设置、手动触发与单部订阅立即搜源。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from csx.api.envelope import ok
from csx.application import auto_search
from csx.infra.db import get_db
from csx.infra.models import Subscription

router = APIRouter(prefix="/auto_search", tags=["auto_search"])


class AutoSearchSettings(BaseModel):
    enabled: bool | None = None
    interval_hours: int | None = Field(default=None, ge=1, le=168)
    auto_transfer: bool | None = None
    max_per_round: int | None = Field(default=None, ge=1, le=50)
    per_subscription_limit: int | None = Field(default=None, ge=5, le=50)


class RunRequest(BaseModel):
    subscription_id: int | None = Field(default=None, gt=0)
    force: bool = True
    dry_run: bool = False


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)) -> dict[str, Any]:
    return ok(auto_search.load_settings(db))


@router.put("/settings")
def put_settings(body: AutoSearchSettings, db: Session = Depends(get_db)) -> dict[str, Any]:
    return ok(auto_search.save_settings(db, body.model_dump(exclude_none=True)))


@router.post("/run")
def run_now(body: RunRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    if body.subscription_id is not None:
        subscription = db.get(Subscription, body.subscription_id)
        if subscription is None:
            raise HTTPException(
                404, detail={"code": "SUBSCRIPTION_NOT_FOUND", "message": "订阅不存在"}
            )
        config = auto_search.load_settings(db)
        result = auto_search.search_subscription(
            db,
            subscription,
            limit=int(config["per_subscription_limit"]),
            auto_transfer=bool(config["auto_transfer"]) and not body.dry_run,
            dry_run=body.dry_run,
        )
        return ok({"ok": True, "mode": "single", "result": result})
    result = auto_search.run_round(db, force=body.force)
    return ok({"ok": True, "mode": "round", "result": result})
