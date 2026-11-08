"""Preview and execute organization of a drive staging directory."""

from __future__ import annotations

from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.api.envelope import ok
from csx.application.organize_scan import plan_organize
from csx.infra.db import get_db
from csx.infra.drive_runtime import drive_for
from csx.infra.models import Episode, LibraryFile, MediaItem, Season
from csx.infra.settings import settings

router = APIRouter(prefix="/organize", tags=["organize"])


class OrganizeScanRequest(BaseModel):
    account_id: int = Field(gt=0)
    source_path: str = Field(min_length=1, max_length=1024)


class OrganizeExecuteRequest(OrganizeScanRequest):
    file_ids: list[str] = Field(min_length=1, max_length=500)


def _get_drive(request: Request, db: Session, account_id: int):
    from csx.infra.models import Account

    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(404, detail={"code": "ACCOUNT_NOT_FOUND", "message": "账号不存在"})
    drives = getattr(request.app.state, "drives", {})
    drive = drive_for(db, account.provider, drives)
    if drive is None:
        raise HTTPException(
            404, detail={"code": "ACCOUNT_NOT_CONFIGURED", "message": "网盘账号未配置"}
        )
    return account.provider, drive


def _plan(db: Session, drive, source_path: str):
    files = drive.list_dir(source_path)
    media = db.scalars(select(MediaItem)).all()
    return plan_organize(files, media, settings.library_root)


@router.post("/scan")
def scan(body: OrganizeScanRequest, request: Request, db: Session = Depends(get_db)):
    _, drive = _get_drive(request, db, body.account_id)
    try:
        result = _plan(db, drive, body.source_path)
    except Exception as error:
        raise HTTPException(
            502, detail={"code": "DRIVE_SCAN_FAILED", "message": str(error)}
        ) from error
    return ok(result)


@router.post("/execute")
def execute(body: OrganizeExecuteRequest, request: Request, db: Session = Depends(get_db)):
    provider, drive = _get_drive(request, db, body.account_id)
    try:
        plan = _plan(db, drive, body.source_path)
    except Exception as error:
        raise HTTPException(
            502, detail={"code": "DRIVE_SCAN_FAILED", "message": str(error)}
        ) from error
    selected = set(body.file_ids)
    available = {row["file_id"]: row for row in plan["matched"] if row["file_id"] in selected}
    if selected != set(available):
        raise HTTPException(
            422,
            detail={
                "code": "ORGANIZE_SELECTION_INVALID",
                "message": "所选文件包含无法识别或不存在的文件",
            },
        )
    moved = []
    errors = []
    source_directories: set[str] = set()
    for file_id, row in available.items():
        try:
            target = PurePosixPath(row["target_path"])
            drive.move(file_id, str(target.parent))
            drive.rename(file_id, target.name)
            source_directories.add(str(PurePosixPath(row["source_path"]).parent))
            season = db.scalar(
                select(Season).where(
                    Season.media_id == row["media_id"], Season.season_number == row["season"]
                )
            )
            if season is None:
                season = Season(media_id=row["media_id"], season_number=row["season"])
                db.add(season)
                db.flush()
            episode = db.scalar(
                select(Episode).where(
                    Episode.season_id == season.id, Episode.episode_number == row["episode"]
                )
            )
            if episode is None:
                episode = Episode(season_id=season.id, episode_number=row["episode"])
                db.add(episode)
                db.flush()
            existing = db.scalar(
                select(LibraryFile).where(
                    LibraryFile.episode_id == episode.id, LibraryFile.path == row["target_path"]
                )
            )
            if existing is None:
                db.add(
                    LibraryFile(
                        episode_id=episode.id,
                        path=row["target_path"],
                        size=row["size"],
                        quality_bucket=row["quality_bucket"],
                        provider=provider,
                    )
                )
            else:
                existing.size = row["size"]
                existing.quality_bucket = row["quality_bucket"]
                existing.provider = provider
            moved.append(file_id)
        except Exception as error:
            errors.append({"file_id": file_id, "error": str(error)})
    db.commit()
    cleaned = 0
    import contextlib

    for directory in sorted(source_directories, key=lambda value: value.count("/"), reverse=True):
        if directory != body.source_path.rstrip("/"):
            with contextlib.suppress(Exception):
                cleaned += int(bool(drive.delete_empty_directory(directory)))
    return ok({"moved": moved, "errors": errors, "cleaned_directories": cleaned})
