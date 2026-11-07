"""SQLAlchemy persistence for transferred episode files."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.adapters.db.repositories import SqlAlchemyTaskRepository
from csx.infra.models import (
    DiscoveredResource,
    Episode,
    LibraryFile,
    MediaItem,
    Season,
    Subscription,
)


class SqlAlchemyLibraryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_episode_file(
        self,
        *,
        media_id: int,
        season: int,
        episode: int,
        path: str,
        size: int,
        sha1: str,
        quality_bucket: str = "sd",
    ) -> int:
        season_row = self.session.scalar(
            select(Season).where(Season.media_id == media_id, Season.season_number == season)
        )
        if season_row is None:
            season_row = Season(media_id=media_id, season_number=season)
            self.session.add(season_row)
            self.session.flush()
        episode_row = self.session.scalar(
            select(Episode).where(
                Episode.season_id == season_row.id, Episode.episode_number == episode
            )
        )
        if episode_row is None:
            episode_row = Episode(season_id=season_row.id, episode_number=episode)
            self.session.add(episode_row)
            self.session.flush()
        row = self.session.scalar(
            select(LibraryFile)
            .where(LibraryFile.episode_id == episode_row.id)
            .order_by(LibraryFile.id)
            .limit(1)
        )
        if row is None:
            row = LibraryFile(episode_id=episode_row.id, path=path)
            self.session.add(row)
        row.path, row.size, row.sha1, row.quality_bucket = path, size, sha1 or None, quality_bucket
        self.session.flush()
        return row.id

    def update_path(self, *, file_id: str, old_path: str, new_path: str) -> None:
        row = self.session.scalar(select(LibraryFile).where(LibraryFile.path == old_path))
        if row is not None:
            row.path = new_path
            self.session.flush()


class SqlAlchemyTransferRepositories:
    """P3 application repository bundle backed by the existing P1 schema."""

    def __init__(self, session: Session, on_task_transition=None) -> None:
        self.session = session
        self.tasks = SqlAlchemyTaskRepository(session, on_task_transition)
        self.library = SqlAlchemyLibraryRepository(session)

    def get_resource(self, resource_id: int) -> dict | None:
        row = self.session.get(DiscoveredResource, resource_id)
        if row is None:
            return None
        subscription = self.session.get(Subscription, row.subscription_id)
        payload = json.loads(row.payload or "{}")
        media_id = subscription.media_id if subscription else None
        media = self.session.get(MediaItem, media_id) if media_id is not None else None
        return {
            **payload,
            "id": row.id,
            "provider": row.provider,
            "share_url": row.share_url,
            "subscription_id": row.subscription_id,
            "media_id": media_id,
            "media": (
                {"title": media.title, "type": media.type, "year": media.year}
                if media is not None
                else None
            ),
            "idempotency_key": row.idempotency_key,
        }

    def get_media(self, media_id: int) -> dict | None:
        row = self.session.get(MediaItem, media_id)
        return {"title": row.title, "type": row.type, "year": row.year} if row is not None else None
