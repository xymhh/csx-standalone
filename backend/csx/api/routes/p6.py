"""P6 check-in and STRM resource endpoints."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.adapters.db.checkins import SqlAlchemyCheckinRepository
from csx.adapters.db.strm import SqlAlchemyStrmRepository
from csx.adapters.drive.registry import DriveRegistry
from csx.adapters.media.emby import server_clients
from csx.api.envelope import ok
from csx.application.checkin import CheckinOutcome
from csx.application.strm import StrmService
from csx.infra.checkin_runtime import checkin_accounts
from csx.infra.db import get_db
from csx.infra.models import Account, CheckinRecord, Setting
from csx.infra.side_effects import dispatch_notification

checkin = APIRouter(prefix="/checkin", tags=["checkin"])
strm = APIRouter(prefix="/strm", tags=["strm"])


class CheckinRunRequest(BaseModel):
    account_id: int | None = Field(default=None, gt=0)


class StrmSyncRequest(BaseModel):
    library_file_id: int | None = Field(default=None, gt=0)
    clean_missing: bool = False


def _settings_section(db: Session, name: str) -> dict[str, Any]:
    rows = db.scalars(select(Setting).where(Setting.key.like(f"{name}.%")))
    return {row.key.split(".", 1)[1]: json.loads(row.value) for row in rows}


def _outcome_data(outcome: CheckinOutcome) -> dict[str, Any]:
    return outcome.as_dict()


def _history_data(row: CheckinRecord) -> dict[str, Any]:
    return {
        "id": row.id,
        "account_id": row.account_id,
        "provider": row.provider,
        "account_name": row.account_name,
        "checked_at": row.checked_at,
        "success": bool(row.success),
        "reward": row.reward,
        "message": row.message,
        "consecutive_days": row.consecutive_days,
        "details": json.loads(row.details or "{}"),
    }


@checkin.post("/run")
def run_checkin(
    background_tasks: BackgroundTasks,
    body: CheckinRunRequest | None = None,
    db: Session = Depends(get_db),
):
    if body and body.account_id is not None and db.get(Account, body.account_id) is None:
        raise HTTPException(404, detail={"code": "ACCOUNT_NOT_FOUND", "message": "账号不存在"})
    outcomes = checkin_accounts(db, body.account_id if body else None)
    if outcomes:
        background_tasks.add_task(
            dispatch_notification,
            _settings_section(db, "notify"),
            "checkin_report",
            {"results": [_outcome_data(outcome) for outcome in outcomes]},
        )
    return ok(
        {
            "total": len(outcomes),
            "succeeded": sum(outcome.success for outcome in outcomes),
            "failed": sum(not outcome.success for outcome in outcomes),
            "results": [_outcome_data(outcome) for outcome in outcomes],
        }
    )


@checkin.get("/history")
def checkin_history(
    account_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = SqlAlchemyCheckinRepository(db).list(account_id=account_id, limit=limit)
    return ok([_history_data(row) for row in rows])


@strm.post("/sync")
def sync_strm(
    request: Request,
    body: StrmSyncRequest | None = None,
    db: Session = Depends(get_db),
):
    config = _settings_section(db, "strm")
    is_direct = str(config.get("mode") or "local_mount").lower() == "direct"
    drives = {}
    if is_direct:
        drives = getattr(request.app.state, "drives", None) or DriveRegistry.from_session(db)
    service = StrmService(SqlAlchemyStrmRepository(db), strm_settings=config, drives=drives)
    try:
        result = service.sync(
            library_file_id=body.library_file_id if body else None,
            clean_missing=body.clean_missing if body else False,
        )
    except ValueError as error:
        raise HTTPException(
            422, detail={"code": "INVALID_STRM_CONFIG", "message": str(error)}
        ) from error
    db.commit()
    refreshes = []
    if result.generated:
        for client in server_clients(_settings_section(db, "advanced")):
            try:
                client.refresh()
                refreshes.append({"provider": client.provider, "valid": True})
            except Exception as error:
                refreshes.append(
                    {"provider": client.provider, "valid": False, "message": str(error)}
                )
            finally:
                client.close()
    return ok(
        {
            "generated": result.generated,
            "unchanged": result.unchanged,
            "removed": result.removed,
            "errors": list(result.errors),
            "server_refreshes": refreshes,
        }
    )


@strm.get("/records")
def strm_records(
    library_file_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=500, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    rows = SqlAlchemyStrmRepository(db).list_records(library_file_id=library_file_id)
    return ok(rows[:limit])
