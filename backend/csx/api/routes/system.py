"""System maintenance endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from csx.api.envelope import ok
from csx.infra.backup import create_backup, list_backups
from csx.infra.db import engine
from csx.infra.settings import settings

router = APIRouter(prefix="/system", tags=["system"])


@router.post("/backup")
def create_system_backup():
    try:
        return ok(create_backup(engine, settings.data_dir / "backups"))
    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=500,
            detail={"code": "BACKUP_FAILED", "message": str(error)},
        ) from error


@router.get("/backups")
def get_system_backups():
    return ok(list_backups(settings.data_dir / "backups"))
