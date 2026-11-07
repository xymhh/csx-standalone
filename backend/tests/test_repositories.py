from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from csx.adapters.db.repositories import (
    SqlAlchemyMediaRepository,
    SqlAlchemySubscriptionRepository,
    SqlAlchemyTaskRepository,
)
from csx.domain.media import Episode, EpisodeKey, MediaItem, MediaType, Season
from csx.domain.subscription import SubscriptionScope
from csx.domain.task import InvalidTransition, TaskState
from csx.infra.models import (
    Base,
    LibraryFile,
    TransferTask,
)
from csx.infra.models import (
    Episode as EpisodeRow,
)
from csx.infra.models import (
    MediaItem as MediaItemRow,
)
from csx.infra.models import (
    Season as SeasonRow,
)


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'repositories.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        yield db
        db.rollback()
    engine.dispose()


def test_media_upsert_is_idempotent_and_owned_episodes_joins_library(session) -> None:
    repository = SqlAlchemyMediaRepository(session)
    media = MediaItem(123, MediaType.TV, "Example", 2024)
    media_id = repository.upsert(media)
    assert repository.upsert(media) == media_id
    assert session.scalar(select(func.count()).select_from(MediaItemRow)) == 1

    season = SeasonRow(media_id=media_id, season_number=1)
    session.add(season)
    session.flush()
    episode = EpisodeRow(season_id=season.id, episode_number=2, air_date=date(2024, 1, 1))
    session.add(episode)
    session.flush()
    session.add(LibraryFile(episode_id=episode.id, path="/library/episode.mkv"))
    session.flush()
    assert repository.owned_episodes(media_id) == {EpisodeKey(1, 2)}
    assert repository.get_by_tmdb(123) == MediaItem(
        123,
        MediaType.TV,
        "Example",
        2024,
        (Season(1, (Episode(EpisodeKey(1, 2), date(2024, 1, 1)),)),),
    )


def test_subscription_and_task_repository_behavior(session) -> None:
    media_id = SqlAlchemyMediaRepository(session).upsert(MediaItem(1, MediaType.MOVIE, "Film"))
    subscriptions = SqlAlchemySubscriptionRepository(session)
    sub_id = subscriptions.create(media_id, SubscriptionScope(), source="test")
    assert subscriptions.get(sub_id)["state"] == "active"
    assert subscriptions.list_active()[0]["id"] == sub_id

    tasks = SqlAlchemyTaskRepository(session)
    task_id, created = tasks.create_or_get("once", subscription_id=sub_id)
    assert created is True
    assert tasks.create_or_get("once", subscription_id=sub_id) == (task_id, False)
    with pytest.raises(InvalidTransition):
        tasks.transition(task_id, TaskState.SUCCEEDED)
    assert tasks.transition(task_id, TaskState.RUNNING) is TaskState.RUNNING


def test_due_only_returns_queued_or_retry_tasks_due_by_now(session) -> None:
    tasks = SqlAlchemyTaskRepository(session)
    now = datetime(2026, 11, 7, 12)
    due = TransferTask(idempotency_key="due", next_retry_at=now - timedelta(seconds=1))
    future = TransferTask(idempotency_key="future", next_retry_at=now + timedelta(seconds=1))
    retry = TransferTask(idempotency_key="retry", state="retry_wait", next_retry_at=now, attempt=1)
    session.add_all((due, future, retry))
    session.flush()
    assert {row["idempotency_key"] for row in tasks.due(now)} == {"due", "retry"}


def test_due_includes_freshly_created_queued_task(session) -> None:
    """新建任务 next_retry_at 为 NULL，必须立刻可被调度器捞到。"""
    tasks = SqlAlchemyTaskRepository(session)
    task_id, _ = tasks.create_or_get("fresh")
    assert [row["id"] for row in tasks.due(datetime(2026, 11, 7, 12))] == [task_id]
