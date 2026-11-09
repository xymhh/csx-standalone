"""跨盘转存设置：媒体库网盘、缓存与并发参数。"""

from __future__ import annotations

import shutil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from csx.api.envelope import ok
from csx.infra.cross_transfer import (
    SUPPORTED_PROVIDERS,
    enabled_accounts,
    load_cross_settings,
    resolve_cache_dir,
    resolve_library_drive,
    save_cross_settings,
)
from csx.infra.db import get_db

router = APIRouter(prefix="/settings/cross", tags=["settings"])

_LABELS = {"115": "115 网盘", "quark": "夸克网盘"}


@router.get("/config")
def get_transfer_settings(db: Session = Depends(get_db)):
    cfg = load_cross_settings(db)
    accounts = enabled_accounts(db)
    cache_dir = resolve_cache_dir(cfg)
    try:
        free = int(shutil.disk_usage(cache_dir).free)
    except OSError:
        free = 0
    return ok(
        {
            **cfg,
            "library_drive": resolve_library_drive(db, cfg),
            "cache_dir": str(cache_dir),
            "cache_free_gb": round(free / (1024**3), 1),
            "drive_options": [
                {
                    "value": provider,
                    "label": _LABELS.get(provider, provider),
                    "primary": bool(getattr(account, "is_primary", False)),
                }
                for provider, account in accounts.items()
            ],
        }
    )


@router.post("/config")
def save_transfer_settings(body: dict, db: Session = Depends(get_db)):
    payload = body or {}
    drive = str(payload.get("library_drive") or "").strip().lower()
    if drive and drive not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            422,
            detail={"code": "INVALID_LIBRARY_DRIVE", "message": "媒体库网盘只能是 115 或夸克"},
        )
    if drive and drive not in enabled_accounts(db):
        raise HTTPException(
            422,
            detail={
                "code": "LIBRARY_DRIVE_NOT_CONFIGURED",
                "message": f"还没有绑定 {_LABELS.get(drive, drive)} 账号",
            },
        )
    saved = save_cross_settings(db, {**payload, "library_drive": drive})
    return ok(saved)
