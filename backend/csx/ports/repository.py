"""Repository interfaces used by application services."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from csx.domain.media import EpisodeKey, MediaItem
from csx.domain.subscription import SubscriptionScope
from csx.domain.task import TaskState


class MediaRepository(Protocol):
    def upsert(self, item: MediaItem) -> int: ...

    def get_by_tmdb(self, tmdb_id: int) -> MediaItem | None: ...

    def owned_episodes(self, media_id: int) -> set[EpisodeKey]: ...


class SubscriptionRepository(Protocol):
    def create(
        self,
        media_id: int,
        scope: SubscriptionScope,
        quality_pref: str = '{"min_bucket":"1080p"}',
        source: str = "manual",
    ) -> int: ...

    def get(self, sub_id: int) -> dict | None: ...

    def list_active(self) -> list[dict]: ...

    def set_state(self, sub_id: int, state: str) -> None: ...


class TaskRepository(Protocol):
    def create_or_get(
        self,
        idempotency_key: str,
        *,
        subscription_id: int | None = None,
        resource_id: int | None = None,
    ) -> tuple[int, bool]: ...

    def transition(self, task_id: int, dst: TaskState, *, error: str = "") -> TaskState: ...

    def get(self, task_id: int) -> dict | None: ...

    def due(self, now: datetime, limit: int = 100) -> list[dict]: ...
