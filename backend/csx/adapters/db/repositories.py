"""SQLAlchemy implementations of the domain repository ports."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from csx.domain.media import Episode, EpisodeKey, MediaItem, MediaType, Season
from csx.domain.subscription import SubscriptionScope
from csx.domain.task import TaskState, assert_transition, next_retry_at
from csx.infra.models import (
    Episode as EpisodeRow,
)
from csx.infra.models import (
    LibraryFile,
    Subscription,
    TransferTask,
)
from csx.infra.models import (
    MediaItem as MediaItemRow,
)
from csx.infra.models import (
    Season as SeasonRow,
)


class SqlAlchemyMediaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, item: MediaItem) -> int:
        row = self.session.scalar(select(MediaItemRow).where(MediaItemRow.tmdb_id == item.tmdb_id))
        if row is None:
            row = MediaItemRow(
                tmdb_id=item.tmdb_id, type=item.type.value, title=item.title, year=item.year
            )
            self.session.add(row)
        else:
            row.type = item.type.value
            row.title = item.title
            row.year = item.year
        self.session.flush()
        return row.id

    def get_by_tmdb(self, tmdb_id: int) -> MediaItem | None:
        row = self.session.scalar(select(MediaItemRow).where(MediaItemRow.tmdb_id == tmdb_id))
        if row is None:
            return None
        seasons: list[Season] = []
        season_rows = self.session.scalars(
            select(SeasonRow).where(SeasonRow.media_id == row.id).order_by(SeasonRow.season_number)
        ).all()
        for season_row in season_rows:
            episode_rows = self.session.scalars(
                select(EpisodeRow)
                .where(EpisodeRow.season_id == season_row.id)
                .order_by(EpisodeRow.episode_number)
            ).all()
            episodes = tuple(
                Episode(
                    EpisodeKey(season_row.season_number, episode.episode_number),
                    episode.air_date,
                    episode.title,
                )
                for episode in episode_rows
            )
            seasons.append(Season(season_row.season_number, episodes))
        return MediaItem(row.tmdb_id, MediaType(row.type), row.title, row.year, tuple(seasons))

    def owned_episodes(self, media_id: int) -> set[EpisodeKey]:
        rows = self.session.execute(
            select(SeasonRow.season_number, EpisodeRow.episode_number)
            .join(EpisodeRow, EpisodeRow.season_id == SeasonRow.id)
            .join(LibraryFile, LibraryFile.episode_id == EpisodeRow.id)
            .where(SeasonRow.media_id == media_id)
        )
        return {EpisodeKey(season_number, episode_number) for season_number, episode_number in rows}


class SqlAlchemySubscriptionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        media_id: int,
        scope: SubscriptionScope,
        quality_pref: str = '{"min_bucket":"1080p"}',
        source: str = "manual",
    ) -> int:
        row = Subscription(
            media_id=media_id, scope=scope.to_json(), quality_pref=quality_pref, source=source
        )
        self.session.add(row)
        self.session.flush()
        return row.id

    @staticmethod
    def _as_dict(row: Subscription) -> dict:
        return {
            "id": row.id,
            "media_id": row.media_id,
            "scope": SubscriptionScope.from_json(row.scope),
            "quality_pref": row.quality_pref,
            "state": row.state,
            "source": row.source,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def get(self, sub_id: int) -> dict | None:
        row = self.session.get(Subscription, sub_id)
        return self._as_dict(row) if row is not None else None

    def list_active(self) -> list[dict]:
        rows = self.session.scalars(
            select(Subscription).where(Subscription.state == "active").order_by(Subscription.id)
        )
        return [self._as_dict(row) for row in rows]

    def set_state(self, sub_id: int, state: str) -> None:
        row = self.session.get(Subscription, sub_id)
        if row is not None:
            row.state = state
            row.updated_at = datetime.now(UTC).replace(tzinfo=None)
            self.session.flush()


class SqlAlchemyTaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_or_get(
        self,
        idempotency_key: str,
        *,
        subscription_id: int | None = None,
        resource_id: int | None = None,
    ) -> tuple[int, bool]:
        row = self.session.scalar(
            select(TransferTask).where(TransferTask.idempotency_key == idempotency_key)
        )
        if row is not None:
            return row.id, False
        row = TransferTask(
            idempotency_key=idempotency_key,
            subscription_id=subscription_id,
            resource_id=resource_id,
        )
        self.session.add(row)
        self.session.flush()
        return row.id, True

    def transition(self, task_id: int, dst: TaskState, *, error: str = "") -> TaskState:
        row = self.session.get(TransferTask, task_id)
        if row is None:
            raise LookupError(f"Task {task_id} does not exist")
        src = TaskState(row.state)
        assert_transition(src, dst)
        now = datetime.now(UTC).replace(tzinfo=None)
        row.state = dst.value
        row.updated_at = now
        if dst is TaskState.RUNNING:
            row.attempt += 1
            row.next_retry_at = None
        elif dst is TaskState.RETRY_WAIT:
            row.next_retry_at = next_retry_at(now, row.attempt)
        elif dst is TaskState.DEAD_LETTER:
            row.dead_letter = 1
        if error:
            row.last_error = error
        self.session.flush()
        return dst

    def due(self, now: datetime, limit: int = 100) -> list[dict]:
        rows = self.session.scalars(
            select(TransferTask)
            .where(
                TransferTask.state.in_((TaskState.QUEUED.value, TaskState.RETRY_WAIT.value)),
                # 新建任务 next_retry_at 为 NULL，表示「立刻可执行」
                or_(
                    TransferTask.next_retry_at.is_(None),
                    TransferTask.next_retry_at <= now,
                ),
            )
            .order_by(TransferTask.next_retry_at, TransferTask.id)
            .limit(limit)
        )
        return [
            {
                "id": row.id,
                "idempotency_key": row.idempotency_key,
                "subscription_id": row.subscription_id,
                "resource_id": row.resource_id,
                "state": row.state,
                "attempt": row.attempt,
                "next_retry_at": row.next_retry_at,
                "dead_letter": row.dead_letter,
                "last_error": row.last_error,
            }
            for row in rows
        ]
