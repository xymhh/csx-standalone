"""115 网盘云端离线下载管理路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from csx.api.envelope import ok
from csx.infra.db import get_db
from csx.infra.drive_runtime import drive_for
from csx.infra.models import Account

router = APIRouter(prefix="/drives/offline", tags=["drives"])


def _get_115_drive(request: Request, db: Session, account_id: int):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(404, detail={"code": "ACCOUNT_NOT_FOUND", "message": "网盘账号不存在"})
    if account.provider.lower() != "115":
        raise HTTPException(
            400,
            detail={
                "code": "OFFLINE_NOT_SUPPORTED",
                "message": f"{account.provider} 网盘暂不支持云端离线下载，目前仅支持 115 网盘",
            },
        )
    drives = getattr(request.app.state, "drives", {})
    drive = drive_for(db, "115", drives)
    if drive is None:
        raise HTTPException(
            404, detail={"code": "ACCOUNT_NOT_CONFIGURED", "message": "115 网盘账号尚未配置"}
        )
    return drive


@router.get("/tasks")
def list_offline_tasks(
    account_id: int = Query(gt=0),
    request: Request = None,
    db: Session = Depends(get_db),
):
    drive = _get_115_drive(request, db, account_id)
    fetcher = getattr(drive, "list_offline_tasks", None)
    if not fetcher:
        return ok([])
    tasks = fetcher()
    return ok(tasks)


class OfflineAddRequest(BaseModel):
    account_id: int = Field(gt=0)
    url: str = Field(min_length=1, max_length=4096)
    parent_id: str = Field(default="0")


@router.post("/add")
def add_offline_task(
    body: OfflineAddRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    drive = _get_115_drive(request, db, body.account_id)
    adder = getattr(drive, "add_offline_task", None)
    if not adder:
        raise HTTPException(501, detail={"code": "NOT_IMPLEMENTED", "message": "离线添加未实现"})
    try:
        res = adder(body.url.strip(), body.parent_id)
        return ok(res)
    except Exception as e:
        raise HTTPException(502, detail={"code": "OFFLINE_ADD_FAILED", "message": str(e)}) from e


class OfflineDeleteRequest(BaseModel):
    account_id: int = Field(gt=0)
    hashes: list[str] = Field(min_length=1, max_length=100)


@router.post("/delete")
def delete_offline_tasks(
    body: OfflineDeleteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    drive = _get_115_drive(request, db, body.account_id)
    deleter = getattr(drive, "delete_offline_tasks", None)
    if not deleter:
        raise HTTPException(501, detail={"code": "NOT_IMPLEMENTED", "message": "离线删除未实现"})
    success = deleter(body.hashes)
    return ok({"deleted": success})
