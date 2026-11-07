import uuid

from p4_helpers import login

from csx.adapters.db.repositories import SqlAlchemyTaskRepository
from csx.domain.task import TaskState
from csx.infra.db import SessionLocal


def _task(state):
    with SessionLocal() as db:
        repo = SqlAlchemyTaskRepository(db)
        task_id, _ = repo.create_or_get(f"p4-task-{state}-{uuid.uuid4().hex}")
        if state == "retry_wait":
            repo.transition(task_id, TaskState.RUNNING)
            repo.transition(task_id, TaskState.RETRY_WAIT, error="temporary")
        elif state == "dead_letter":
            repo.transition(task_id, TaskState.RUNNING)
            repo.transition(task_id, TaskState.FAILED, error="failed")
            repo.transition(task_id, TaskState.DEAD_LETTER, error="failed")
        db.commit()
        return task_id


def test_task_list_retry_cancel_and_business_errors(client):
    login(client)
    retry_id = _task("retry_wait")
    cancel_id = _task("queued")
    dead_id = _task("dead_letter")

    listing = client.get("/api/v1/tasks?state=retry_wait")
    assert listing.status_code == 200
    assert any(row["id"] == retry_id for row in listing.json()["data"])
    assert client.post(f"/api/v1/tasks/{retry_id}/retry").json()["data"]["attempt"] == 0
    assert client.post(f"/api/v1/tasks/{cancel_id}/cancel").json()["data"]["state"] == "cancelled"
    assert client.post(f"/api/v1/tasks/{dead_id}/retry").json()["data"]["state"] == "queued"
    history_id = _task("dead_letter")
    assert client.get("/api/v1/history?provider=quark").status_code == 200
    batch = client.post("/api/v1/history/retry_batch", json=[history_id])
    assert batch.status_code == 200
    assert history_id in batch.json()["data"]["retried"]
    assert client.post(f"/api/v1/tasks/{cancel_id}/retry").status_code == 409
    assert client.get("/api/v1/tasks?state=not-a-state").status_code == 422
    assert client.post("/api/v1/tasks/999999/cancel").status_code == 404
