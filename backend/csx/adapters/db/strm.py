"""SQLAlchemy accessors for library files and STRM records."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.infra.models import Episode, LibraryFile, MediaItem, Season, StrmRecord


class SqlAlchemyStrmRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_library_files(self, *, library_file_id: int | None = None) -> list[dict]:
        query = (
            select(LibraryFile, Episode, Season, MediaItem)
            .join(Episode, LibraryFile.episode_id == Episode.id)
            .join(Season, Episode.season_id == Season.id)
            .join(MediaItem, Season.media_id == MediaItem.id)
            .order_by(LibraryFile.id)
        )
        if library_file_id is not None:
            query = query.where(LibraryFile.id == library_file_id)
        return [
            {
                "id": file.id,
                "media_id": season.media_id,
                "title": media.title,
                "season": season.season_number,
                "episode": episode.episode_number,
                "path": file.path,
                "provider": file.provider,
                "quality_bucket": file.quality_bucket,
            }
            for file, episode, season, media in self.session.execute(query)
        ]

    def upsert_record(self, library_file_id: int, strm_path: str) -> StrmRecord:
        row = self.session.scalar(
            select(StrmRecord).where(StrmRecord.library_file_id == library_file_id)
        )
        if row is None:
            row = StrmRecord(library_file_id=library_file_id, strm_path=strm_path)
            self.session.add(row)
        else:
            row.strm_path = strm_path
            row.generated_at = datetime.now(UTC).replace(tzinfo=None)
        self.session.flush()
        return row

    def list_records(self, *, library_file_id: int | None = None) -> list[dict]:
        query = select(StrmRecord).order_by(StrmRecord.id)
        if library_file_id is not None:
            query = query.where(StrmRecord.library_file_id == library_file_id)
        return [
            {"id": row.id, "library_file_id": row.library_file_id, "strm_path": row.strm_path}
            for row in self.session.scalars(query)
        ]

    def delete_record(self, record_id: int) -> None:
        row = self.session.get(StrmRecord, record_id)
        if row is not None:
            self.session.delete(row)
