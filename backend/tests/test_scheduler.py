import asyncio
import threading
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from csx.adapters.db.repositories import SqlAlchemyTaskRepository
from csx.domain.task import TaskState
from csx.infra.events import EventBus
from csx.infra.models import Base, TransferTask
from csx.infra.scheduler import TaskScheduler, TokenBucket, provider_rate


class FakeScheduler(TaskScheduler):
    def __init__(self, rows, **kwargs):
        super().__init__(drives={}, **kwargs)
        self.rows = rows
        self.running_exec = 0
        self.maximum = 0
        self.executed = []
        self.completed = set()
        self.guard = threading.Lock()
        self.runnable = True

    def _load_due(self):
        return [row for row in self.rows if row["id"] not in self.completed]

    def _resource_for_task(self, row):
        return {"provider": row.get("provider", "115")}

    def _task_is_runnable(self, task_id):
        return self.runnable

    def _execute(self, row):
        with self.guard:
            self.running_exec += 1
            self.maximum = max(self.maximum, self.running_exec)
            self.executed.append(row["id"])
        time.sleep(0.01)
        with self.guard:
            self.running_exec -= 1
            self.completed.add(row["id"])
        return {}, [(row["id"], "queued", "succeeded", "")], "succeeded"


def _rows(count, *, same_key=False):
    return [
        {
            "id": index,
            "state": "queued",
            "idempotency_key": "same" if same_key else f"key-{index}",
            "provider": "115",
        }
        for index in range(1, count + 1)
    ]


def test_scheduler_dispatches_due_rows_with_global_limit_eight():
    scheduler = FakeScheduler(_rows(12), max_workers=8)
    scheduler._buckets["115"] = TokenBucket(10000)

    async def run():
        await scheduler.poll_once()
        while len(scheduler.executed) < 12:
            await asyncio.sleep(0.005)
            await scheduler.poll_once()

    asyncio.run(run())

    assert scheduler.maximum <= 8
    assert len(scheduler.executed) == 12


def test_scheduler_serializes_equal_idempotency_keys():
    scheduler = FakeScheduler(_rows(4, same_key=True), max_workers=4)
    scheduler._buckets["115"] = TokenBucket(10000)

    async def run():
        await scheduler.poll_once()
        while len(scheduler.executed) < 4:
            await asyncio.sleep(0.005)
            await scheduler.poll_once()

    asyncio.run(run())

    assert scheduler.maximum == 1
    assert len(scheduler.executed) == 4


def test_scheduler_skips_task_cancelled_while_waiting():
    scheduler = FakeScheduler(_rows(1))
    scheduler.runnable = False

    async def run():
        await scheduler.poll_once()
        await asyncio.gather(*scheduler._workers.values())

    asyncio.run(run())

    assert scheduler.executed == []


def test_scheduler_broadcasts_task_state_transition():
    bus = EventBus()
    scheduler = FakeScheduler(_rows(1), event_stream=bus)
    scheduler._buckets["115"] = TokenBucket(10000)

    async def run():
        async with bus.subscribe() as queue:
            await scheduler.poll_once()
            await asyncio.gather(*scheduler._workers.values())
            return await asyncio.wait_for(queue.get(), timeout=1)

    event = asyncio.run(run())
    assert event["type"] == "task_status"
    assert event["data"]["new_state"] == "succeeded"


def test_token_bucket_waits_for_provider_rate_and_refills():
    now = [100.0]
    bucket = TokenBucket(4, clock=lambda: now[0])

    async def run():
        waits = [await bucket.acquire() for _ in range(4)]
        wait = await bucket.acquire()
        second_wait = await bucket.acquire()
        return waits, wait, second_wait

    waits, wait, second_wait = asyncio.run(run())

    assert waits == [0.0] * 4
    assert wait == 15
    assert second_wait == 30
    assert provider_rate("115") == 4
    assert provider_rate("quark") == 8
    assert provider_rate("other") == 4


def test_task_retry_backoff_is_persisted_by_repository():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as db:
        repo = SqlAlchemyTaskRepository(db)
        task_id, _ = repo.create_or_get("backoff-key")
        repo.transition(task_id, TaskState.RUNNING)
        repo.transition(task_id, TaskState.RETRY_WAIT, error="temporary")
        db.commit()
        retry_at = db.get(TransferTask, task_id).next_retry_at
        now = datetime.now(UTC).replace(tzinfo=None)
        assert now + timedelta(seconds=55) <= retry_at <= now + timedelta(seconds=65)
    engine.dispose()
