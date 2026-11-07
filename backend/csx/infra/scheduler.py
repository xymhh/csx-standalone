"""Async task polling with bounded workers, per-key serialization and rate buckets."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from starlette.concurrency import run_in_threadpool

from csx.adapters.db.repositories import SqlAlchemyTaskRepository
from csx.adapters.drive.registry import DriveRegistry
from csx.adapters.library import SqlAlchemyTransferRepositories
from csx.application.transfer import execute_transfer
from csx.domain.task import TaskState
from csx.infra.db import SessionLocal
from csx.infra.events import EventBus, event_bus
from csx.infra.settings import settings


class TokenBucket:
    """Thread-safe-by-event-loop token bucket with a one-minute capacity."""

    def __init__(self, rate_per_minute: int, clock: Callable[[], float] | None = None) -> None:
        import time

        self.rate = rate_per_minute
        self.capacity = float(rate_per_minute)
        self.tokens = float(rate_per_minute)
        self._clock = clock or time.monotonic
        self.updated = self._clock()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        async with self._lock:
            now = self._clock()
            self.tokens = min(
                self.capacity, self.tokens + max(0, now - self.updated) * self.rate / 60
            )
            self.updated = now
            if self.tokens >= 1:
                self.tokens -= 1
                return 0.0
            wait = (1 - self.tokens) * 60 / self.rate
            self.tokens -= 1.0
            self.updated = now
            return wait


def provider_rate(provider: str) -> int:
    return {"115": 4, "quark": 8}.get(provider.lower(), 4)


class TaskScheduler:
    def __init__(
        self,
        *,
        drives: dict[str, Any] | None = None,
        event_stream: EventBus = event_bus,
        interval_seconds: float = 30,
        max_workers: int = 8,
        session_factory=SessionLocal,
    ) -> None:
        self.drives = drives if drives is not None else {}
        self.events = event_stream
        self.interval_seconds = interval_seconds
        self.max_workers = max_workers
        self.session_factory = session_factory
        self._poller: asyncio.Task | None = None
        self._workers: dict[int, asyncio.Task] = {}
        self._claimed_keys: set[str] = set()
        self._key_locks: dict[str, asyncio.Lock] = {}
        self._buckets: dict[str, TokenBucket] = {}
        self._stopping = False
        self._waiting_queue_depth = 0

    async def start(self) -> None:
        if self._poller is None or self._poller.done():
            self._stopping = False
            self._poller = asyncio.create_task(self._poll_loop(), name="csx-task-poller")

    async def stop(self) -> None:
        self._stopping = True
        if self._poller:
            self._poller.cancel()
            await asyncio.gather(self._poller, return_exceptions=True)
            self._poller = None
        workers = list(self._workers.values())
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)
        self._workers.clear()
        self._claimed_keys.clear()

    async def _poll_loop(self) -> None:
        while not self._stopping:
            await self.poll_once()
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    async def poll_once(self) -> int:
        self._workers = {task_id: job for task_id, job in self._workers.items() if not job.done()}
        due_rows = await run_in_threadpool(self._load_due)
        dispatched = 0
        for row in due_rows:
            if len(self._workers) >= self.max_workers:
                break
            key = str(row["idempotency_key"])
            if key in self._claimed_keys:
                continue
            self._claimed_keys.add(key)
            task_id = int(row["id"])
            job = asyncio.create_task(self._run_task(row), name=f"csx-task-{task_id}")
            self._workers[task_id] = job
            job.add_done_callback(
                lambda _job, ident=task_id, task_key=key: self._release(ident, task_key)
            )
            dispatched += 1
        self._waiting_queue_depth = sum(int(row["id"]) not in self._workers for row in due_rows)
        return dispatched

    def _release(self, task_id: int, key: str) -> None:
        self._workers.pop(task_id, None)
        self._claimed_keys.discard(key)

    def _load_due(self) -> list[dict]:
        with self.session_factory() as db:
            return SqlAlchemyTaskRepository(db).due(datetime.now(UTC).replace(tzinfo=None))

    async def _run_task(self, row: dict) -> None:
        provider = "unknown"
        try:
            resource = await run_in_threadpool(self._resource_for_task, row)
            provider = str(resource.get("provider", "unknown")).lower()
            bucket = self._buckets.setdefault(provider, TokenBucket(provider_rate(provider)))
            wait = await bucket.acquire()
            if wait:
                await asyncio.sleep(wait)
            if not await run_in_threadpool(self._task_is_runnable, int(row["id"])):
                return
            lock = self._key_locks.setdefault(str(row["idempotency_key"]), asyncio.Lock())
            async with lock:
                result, transitions, _new_state = await run_in_threadpool(self._execute, row)
            for task_id, old_state, next_state, error in transitions:
                await self.events.publish(
                    "task_status",
                    {
                        "task_id": task_id,
                        "old_state": old_state,
                        "new_state": next_state,
                        "error": error or result.get("error", ""),
                    },
                )
            if result.get("ok") and resource.get("media_id") is not None:
                await self.events.publish(
                    "progress_update", {"media_id": resource["media_id"], "task_id": row["id"]}
                )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await self.events.publish(
                "task_status",
                {
                    "task_id": row.get("id"),
                    "old_state": row.get("state"),
                    "new_state": "error",
                    "error": str(error),
                },
            )

    def _resource_for_task(self, row: dict) -> dict:
        with self.session_factory() as db:
            repos = SqlAlchemyTransferRepositories(db)
            resource = repos.get_resource(row["resource_id"])
            return resource or {}

    def _task_is_runnable(self, task_id: int) -> bool:
        with self.session_factory() as db:
            task = SqlAlchemyTaskRepository(db).get(task_id)
            return bool(task and task["state"] in {"queued", "retry_wait"})

    def _execute(self, row: dict) -> tuple[dict, list[tuple[int, str, str, str]], str]:
        with self.session_factory() as db:
            transitions = []
            repos = SqlAlchemyTransferRepositories(
                db,
                lambda task_id, old, new, error: transitions.append((task_id, old, new, error)),
            )
            resource = repos.get_resource(row["resource_id"])
            provider = str((resource or {}).get("provider", "")).lower()
            if provider and provider not in self.drives:
                self.drives.update(DriveRegistry.from_session(db))
            if provider and provider not in self.drives:
                tasks = repos.tasks
                tasks.transition(int(row["id"]), TaskState.RUNNING)
                tasks.transition(
                    int(row["id"]), TaskState.RETRY_WAIT, error=f"未配置 {provider} 网盘账号"
                )
                db.commit()
                return (
                    {"ok": False, "error": f"未配置 {provider} 网盘账号"},
                    transitions,
                    TaskState.RETRY_WAIT.value,
                )
            task_row = dict(row)
            result = execute_transfer(
                db,
                task_row,
                drives=self.drives,
                repos=repos,
                settings=settings,
            )
            db.commit()
            task = repos.tasks.get(int(row["id"]))
            return result, transitions, str((task or {}).get("state", "unknown"))

    @property
    def active_workers(self) -> int:
        return sum(not job.done() for job in self._workers.values())

    @property
    def waiting_queue_depth(self) -> int:
        return self._waiting_queue_depth

    @property
    def running(self) -> bool:
        return self._poller is not None and not self._poller.done()
