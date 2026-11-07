"""In-process async event fan-out for SSE clients and application events."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any


class EventBus:
    def __init__(self, queue_size: int = 100) -> None:
        self._queues: set[asyncio.Queue] = set()
        self._queue_size = queue_size
        self._lock = asyncio.Lock()

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        event = {"type": event_type, "data": data}
        async with self._lock:
            for queue in tuple(self._queues):
                if queue.full():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        continue
                queue.put_nowait(event)

    @asynccontextmanager
    async def subscribe(self):
        queue = asyncio.Queue(self._queue_size)
        async with self._lock:
            self._queues.add(queue)
        try:
            yield queue
        finally:
            async with self._lock:
                self._queues.discard(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._queues)


event_bus = EventBus()
