"""追剧进度与媒体库 API（原 routes/resources.py 拆分）。"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.adapters.media.emby import server_clients
from csx.api.envelope import ok
from csx.api.routes.resource_common import _page, _raise
from csx.infra.db import get_db
from csx.infra.models import (
    Episode,
    LibraryFile,
    MediaItem,
    Season,
    Setting,
    Subscription,
)

progress = APIRouter(prefix="/progress", tags=["progress"])
library = APIRouter(prefix="/library", tags=["library"])


def _preferred_subscriptions(db: Session, media_id: int | None = None) -> dict[int, Subscription]:
    query = select(Subscription).where(Subscription.state != "deleted")
    if media_id is not None:
        query = query.where(Subscription.media_id == media_id)
    mapping: dict[int, Subscription] = {}
    for row in db.scalars(query.order_by(Subscription.id)).all():
        current = mapping.get(row.media_id)
        if current is None or (current.state != "active" and row.state == "active"):
            mapping[row.media_id] = row
    return mapping


@progress.get("")
def progress_overview(db: Session = Depends(get_db)):
    media_rows = db.scalars(select(MediaItem).order_by(MediaItem.id)).all()
    subscriptions_by_media = _preferred_subscriptions(db)
    # 「我的追剧」只展示仍有追更订阅的影视：删除订阅后卡片应随之消失
    return ok(
        [
            _media_progress(db, media, subscriptions_by_media[media.id])
            for media in media_rows
            if media.id in subscriptions_by_media
        ]
    )


def _media_progress(
    db: Session, media: MediaItem, subscription: Subscription | None = None
) -> dict:
    seasons = db.scalars(select(Season).where(Season.media_id == media.id)).all()
    aired = 0
    owned = 0
    missing = []
    matrix = []
    today = datetime.now(UTC).date()
    for season in seasons:
        episodes = db.scalars(
            select(Episode).where(Episode.season_id == season.id).order_by(Episode.episode_number)
        ).all()
        entries = []
        for episode in episodes:
            file_row = db.scalar(select(LibraryFile).where(LibraryFile.episode_id == episode.id))
            has_aired = episode.air_date is None or episode.air_date <= today
            aired += int(has_aired)
            owned += int(file_row is not None)
            if has_aired and file_row is None:
                missing.append({"season": season.season_number, "episode": episode.episode_number})
            entries.append(
                {
                    "episode": episode.episode_number,
                    "title": episode.title,
                    "air_date": episode.air_date,
                    "aired": has_aired,
                    "owned": file_row is not None,
                    "file": (
                        {
                            "file_id": file_row.id,
                            "path": file_row.path,
                            "size": file_row.size,
                            "sha1": file_row.sha1,
                            "quality_bucket": file_row.quality_bucket,
                            "created_at": file_row.created_at,
                        }
                        if file_row
                        else None
                    ),
                }
            )
        matrix.append({"season": season.season_number, "episodes": entries})
    return {
        "media_id": media.id,
        "title": media.title,
        "type": media.type,
        "year": media.year,
        "overview": media.overview,
        "poster_url": media.poster_url,
        "rating": getattr(media, "rating", None),
        "subscription_id": subscription.id if subscription else None,
        "subscription_state": subscription.state if subscription else None,
        "aired_count": aired,
        "owned_count": owned,
        "missing": missing,
        "seasons": matrix,
    }


@progress.get("/{media_id}")
def media_progress(media_id: int, db: Session = Depends(get_db)):
    media = db.get(MediaItem, media_id)
    if media is None:
        _raise(404, "MEDIA_NOT_FOUND", "媒体不存在")
    subscription = _preferred_subscriptions(db, media_id).get(media_id)
    return ok(_media_progress(db, media, subscription))


@library.get("/files")
def library_files(
    media_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    query = (
        select(LibraryFile, Episode, Season)
        .join(Episode, LibraryFile.episode_id == Episode.id)
        .join(Season, Episode.season_id == Season.id)
    )
    if media_id is not None:
        query = query.where(Season.media_id == media_id)
    rows = _page(db, query.order_by(LibraryFile.id.desc()), page, page_size)
    return ok(
        [
            {
                "id": file.id,
                "media_id": season.media_id,
                "season": season.season_number,
                "episode": episode.episode_number,
                "path": file.path,
                "size": file.size,
                "sha1": file.sha1,
                "quality_bucket": file.quality_bucket,
            }
            for file, episode, season in rows
        ]
    )


@library.get("/servers")
def library_servers(db: Session = Depends(get_db)):
    advanced = {}
    for row in db.scalars(select(Setting).where(Setting.key.like("advanced.%"))):
        advanced[row.key.split(".", 1)[1]] = json.loads(row.value)
    clients = {client.provider: client for client in server_clients(advanced)}
    result = []
    for provider in ("emby", "jellyfin"):
        client = clients.get(provider)
        if client is None:
            result.append({"provider": provider, "configured": False, "valid": None})
            continue
        try:
            info = client.probe()
            result.append(
                {
                    "provider": provider,
                    "configured": True,
                    "valid": True,
                    "name": info.name,
                    "version": info.version,
                }
            )
        except Exception as error:
            result.append(
                {
                    "provider": provider,
                    "configured": True,
                    "valid": False,
                    "message": str(error),
                }
            )
        finally:
            client.close()
    return ok(result)
