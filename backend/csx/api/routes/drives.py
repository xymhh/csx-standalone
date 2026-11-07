"""Drive browsing and share transfer API routes."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.adapters.db.repositories import SqlAlchemyTaskRepository
from csx.api.envelope import ok
from csx.infra.db import get_db
from csx.infra.drive_runtime import drive_for
from csx.infra.models import Account, ManualTransfer, MediaItem

router = APIRouter(prefix="/drives", tags=["drives"])


def _drive_for_request(request: Request, db: Session, provider: str):
    configured = getattr(request.app.state, "drives", None)
    if not isinstance(configured, dict):
        configured = {}
        request.app.state.drives = configured
    drive = drive_for(db, provider, configured)
    if drive is not None:
        configured.setdefault(provider, drive)
    return drive


class ShareInspectRequest(BaseModel):
    provider: Literal["115", "quark", "auto"] = "auto"
    share_url: str = Field(min_length=1)
    password: str = ""


class ShareTransferRequest(BaseModel):
    account_id: int = Field(gt=0)
    share_url: str = Field(min_length=1)
    password: str = ""
    file_ids: list[str] = Field(min_length=1, max_length=500)
    target_dir: str = Field(min_length=1, max_length=1024)
    media_id: int | None = Field(default=None, gt=0)

    @field_validator("target_dir")
    @classmethod
    def normalize_target_dir(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("目标目录不能为空")
        return normalized


@router.get("/{account_id}/folders")
def list_account_folders(
    account_id: int,
    request: Request,
    parent_id: str = "",
    db: Session = Depends(get_db),
):
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(404, detail={"code": "ACCOUNT_NOT_FOUND", "message": "账号不存在"})
    drive = _drive_for_request(request, db, account.provider)
    if drive is None:
        raise HTTPException(
            404,
            detail={"code": "ACCOUNT_NOT_CONFIGURED", "message": "网盘账号尚未配置"},
        )
    try:
        folders = drive.list_directories(parent_id)
    except Exception as error:
        raise HTTPException(
            502,
            detail={"code": "DRIVE_LIST_FAILED", "message": str(error)},
        ) from error
    return ok(
        [
            {
                "id": folder.directory_id,
                "name": folder.name,
                "path": folder.path,
                "has_children": folder.has_children,
            }
            for folder in folders
        ]
    )


@router.post("/share/inspect")
def inspect_share(body: ShareInspectRequest, request: Request, db: Session = Depends(get_db)):
    configured = getattr(request.app.state, "drives", {})
    providers = (
        [body.provider]
        if body.provider != "auto"
        else list(
            dict.fromkeys(
                [account.provider for account in db.scalars(select(Account)).all()]
                + list(configured)
            )
        )
    )
    last_error = "没有可用的网盘账号"
    for provider in providers:
        if provider not in {"115", "quark"}:
            continue
        drive = _drive_for_request(request, db, provider)
        if drive is None:
            continue
        try:
            status = drive.check_share(body.share_url, body.password)
            if not status.valid:
                last_error = status.error or "分享链接无效"
                if body.provider != "auto":
                    break
                continue
            files = drive.list_share_files(body.share_url, body.password)
            return ok(
                {
                    "provider": provider,
                    "share_title": status.share_title or (files[0].name if files else "分享文件"),
                    "files": [
                        {
                            "id": item.file_id,
                            "name": item.name,
                            "size": item.size,
                            "is_dir": item.is_dir,
                        }
                        for item in files
                    ],
                }
            )
        except Exception as error:
            last_error = str(error)
            if body.provider != "auto":
                break
    raise HTTPException(422, detail={"code": "SHARE_INSPECT_FAILED", "message": last_error})


@router.post("/share/transfer")
def queue_share_transfer(
    body: ShareTransferRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    account = db.get(Account, body.account_id)
    if account is None:
        raise HTTPException(404, detail={"code": "ACCOUNT_NOT_FOUND", "message": "账号不存在"})
    if account.provider not in {"115", "quark"}:
        raise HTTPException(
            422, detail={"code": "UNSUPPORTED_PROVIDER", "message": "暂不支持此网盘"}
        )
    if body.media_id is not None and db.get(MediaItem, body.media_id) is None:
        raise HTTPException(404, detail={"code": "MEDIA_NOT_FOUND", "message": "媒体不存在"})
    drive = _drive_for_request(request, db, account.provider)
    if drive is None:
        raise HTTPException(
            404, detail={"code": "ACCOUNT_NOT_CONFIGURED", "message": "网盘账号尚未配置"}
        )
    try:
        status = drive.check_share(body.share_url, body.password)
        if not status.valid:
            raise HTTPException(
                422,
                detail={"code": "SHARE_INVALID", "message": status.error or "分享链接无效"},
            )
        available = {item.file_id for item in drive.list_share_files(body.share_url, body.password)}
        requested = list(dict.fromkeys(body.file_ids))
        if not set(requested).issubset(available):
            raise HTTPException(
                422,
                detail={"code": "SHARE_FILES_INVALID", "message": "所选文件不属于该分享"},
            )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            502,
            detail={"code": "SHARE_VERIFY_FAILED", "message": str(error)},
        ) from error

    identity = "\n".join(
        (account.provider, body.share_url.strip(), body.target_dir, *sorted(requested))
    )
    key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    tasks = SqlAlchemyTaskRepository(db)
    task_id, created = tasks.create_or_get(key, subscription_id=None, resource_id=None)
    if created:
        db.add(
            ManualTransfer(
                task_id=task_id,
                account_id=account.id,
                share_url=body.share_url.strip(),
                password=body.password,
                file_ids=json.dumps(requested),
                target_dir=body.target_dir,
                media_id=body.media_id,
            )
        )
    db.commit()
    return ok({"task_id": task_id, "state": "queued"})
