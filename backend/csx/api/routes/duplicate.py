"""Find and safely remove redundant library versions."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.api.envelope import ok
from csx.domain.upgrade import QUALITY_RANK
from csx.infra.db import get_db
from csx.infra.drive_runtime import drive_for
from csx.infra.models import Episode, LibraryFile, MediaItem, Season, StrmRecord

router = APIRouter(prefix="/library/duplicates", tags=["library"])


def _groups(db: Session):
    grouped = defaultdict(list)
    rows = db.execute(
        select(LibraryFile, Episode, Season, MediaItem)
        .join(Episode, LibraryFile.episode_id == Episode.id)
        .join(Season, Episode.season_id == Season.id)
        .join(MediaItem, Season.media_id == MediaItem.id)
    ).all()
    for file, episode, season, media in rows:
        grouped[(media.id, season.season_number, episode.episode_number)].append((file, media))
    result = []
    for (media_id, season_number, episode_number), entries in grouped.items():
        if len(entries) < 2:
            continue
        ordered = sorted(entries, key=lambda pair: (QUALITY_RANK.get(pair[0].quality_bucket, 0), -pair[0].id), reverse=True)
        keep_id = ordered[0][0].id
        result.append(
            {
                "media_id": media_id,
                "title": ordered[0][1].title,
                "season": season_number,
                "episode": episode_number,
                "keep_file_id": keep_id,
                "files": [
                    {
                        "id": file.id,
                        "path": file.path,
                        "size": file.size,
                        "provider": file.provider,
                        "quality_bucket": file.quality_bucket,
                        "recommended": file.id == keep_id,
                    }
                    for file, _ in ordered
                ],
            }
        )
    return result


@router.get("")
def list_duplicates(db: Session = Depends(get_db)):
    return ok(_groups(db))


class DuplicateCleanRequest(BaseModel):
    file_ids: list[int] = Field(min_length=1, max_length=500)


@router.post("/clean")
def clean_duplicates(body: DuplicateCleanRequest, request: Request, db: Session = Depends(get_db)):
    groups = _groups(db)
    removable = {file["id"] for group in groups for file in group["files"] if not file["recommended"]}
    selected = set(body.file_ids)
    if not selected.issubset(removable):
        raise HTTPException(422, detail={"code": "DUPLICATE_SELECTION_INVALID", "message": "只能清理重复组中的非推荐版本"})
    deleted = []
    failed = []
    configured = getattr(request.app.state, "drives", {})
    for file_id in selected:
        row = db.get(LibraryFile, file_id)
        try:
            if row.provider:
                drive = drive_for(db, row.provider, configured)
                if drive is None or not drive.delete_path(row.path):
                    raise RuntimeError("网盘文件删除失败")
            for record in db.scalars(select(StrmRecord).where(StrmRecord.library_file_id == row.id)).all():
                db.delete(record)
            db.delete(row)
            deleted.append(file_id)
        except Exception as error:
            failed.append({"file_id": file_id, "error": str(error)})
    db.commit()
    return ok({"deleted": deleted, "failed": failed})
