import asyncio

from p4_helpers import login

from csx.api.routes import platform, resources
from csx.infra.events import event_bus


def test_sse_stream_broadcast_heartbeat_and_cleanup(client, monkeypatch):
    login(client)
    # HEARTBEAT_SECONDS 随 event_stream 一起搬到了 platform 模块，打桩目标随之迁移（断言不变）
    monkeypatch.setattr(platform, "HEARTBEAT_SECONDS", 0.01)

    async def exercise():
        response = await resources.event_stream()
        assert response.media_type == "text/event-stream"
        iterator = response.body_iterator.__aiter__()
        first = asyncio.create_task(iterator.__anext__())
        await asyncio.sleep(0)
        await event_bus.publish("task_status", {"task_id": 91, "new_state": "running"})
        payload = await asyncio.wait_for(first, timeout=1)
        assert "event: task_status" in payload
        assert '"task_id": 91' in payload
        heartbeat = await asyncio.wait_for(iterator.__anext__(), timeout=1)
        assert "event: heartbeat" in heartbeat
        await iterator.aclose()

    previous = event_bus.subscriber_count
    asyncio.run(exercise())
    assert event_bus.subscriber_count == previous


def test_events_requires_auth(client):
    client.cookies.clear()
    response = client.get("/api/v1/events")
    assert response.status_code == 401
