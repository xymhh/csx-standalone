import json
import uuid

from p4_helpers import login, media_row

from csx.adapters.db.repositories import SqlAlchemyTaskRepository
from csx.application.failure_label import failure_detail, failure_label
from csx.domain.task import TaskState
from csx.infra.db import SessionLocal
from csx.infra.models import DiscoveredResource, Subscription, TransferTask


def _task_for(media_id: int, *, provider: str = "quark", state: str = "succeeded") -> int:
    with SessionLocal() as db:
        sub = Subscription(media_id=media_id, scope="{}", quality_pref="{}", source="manual")
        db.add(sub)
        db.flush()
        resource = DiscoveredResource(
            subscription_id=sub.id,
            provider=provider,
            share_url=f"https://pan.quark.cn/s/{uuid.uuid4().hex}",
            dedup_key=uuid.uuid4().hex,
            payload=json.dumps(
                {"title": "谷雨 (2026) S01E12 2160p WEB-DL", "season": 1, "episode": 12},
                ensure_ascii=False,
            ),
        )
        db.add(resource)
        db.flush()
        task = TransferTask(
            idempotency_key=uuid.uuid4().hex,
            subscription_id=sub.id,
            resource_id=resource.id,
            state=state,
            attempt=1,
        )
        db.add(task)
        db.commit()
        return task.id


def test_failure_label_mapping():
    assert failure_label("RapidUploadError: 未命中秒传 @ File ...") == "未命中秒传"
    assert failure_label("分享失效") == "分享失效"
    assert failure_label("整理失败：权限不足") == "整理归档失败"
    assert failure_label("") == ""
    assert failure_label("太空泛的未知错误") == "其他失败"
    long_error = "x" * 400
    assert failure_detail(long_error).endswith("…")
    assert len(failure_detail(long_error)) <= 301


def test_running_task_records_stage(client):
    with SessionLocal() as db:
        repo = SqlAlchemyTaskRepository(db)
        task_id, _ = repo.create_or_get(f"stage-{uuid.uuid4().hex}")
        repo.transition(task_id, TaskState.RUNNING)
        assert repo.get(task_id)["stage"] == "checking"
        repo.set_stage(task_id, "organizing")
        assert repo.get(task_id)["stage"] == "organizing"
        repo.transition(task_id, TaskState.SUCCEEDED)
        assert repo.get(task_id)["stage"] == ""
        db.commit()


def test_task_queue_only_lists_active_states(client):
    login(client)
    media_id = media_row()
    done_id = _task_for(media_id, state="succeeded")
    waiting_id = _task_for(media_id, state="retry_wait")

    listing = client.get("/api/v1/tasks?page_size=100").json()["data"]
    ids = {row["id"] for row in listing}
    assert waiting_id in ids
    assert done_id not in ids
    row = next(item for item in listing if item["id"] == waiting_id)
    assert row["media_title"]
    assert row["display_name"] == "谷雨 (2026) S01E12 2160p WEB-DL"
    assert row["provider"] == "quark"
    assert row["season"] == 1 and row["episode"] == 12
    assert row["stage_label"] is not None


def test_history_groups_by_media_with_detail(client):
    login(client)
    media_id = media_row()
    first = _task_for(media_id, state="succeeded")
    second = _task_for(media_id, provider="115", state="dead_letter")
    with SessionLocal() as db:
        db.get(TransferTask, second).last_error = "RapidUploadError: 未命中秒传 @ File x"
        db.commit()

    payload = client.get("/api/v1/history?page_size=50").json()["data"]
    assert payload["total"] >= 1
    group = next(item for item in payload["groups"] if item["media_id"] == media_id)
    assert group["counts"] == {"succeeded": 1, "failed": 1, "skipped": 0}
    assert group["failure_labels"][0] == {"label": "未命中秒传", "count": 1}
    assert sorted(group["providers"]) == ["115", "quark"]
    assert {record["id"] for record in group["records"]} == {first, second}
    by_id = {record["id"]: record for record in group["records"]}
    assert by_id[first]["failure_detail"] == ""
    assert by_id[second]["failure_detail"].startswith("RapidUploadError")
    assert set(payload["filter_options"]["providers"]) >= {"115", "quark"}

    filtered = client.get("/api/v1/history?provider=115&page_size=50").json()["data"]
    group = next(item for item in filtered["groups"] if item["media_id"] == media_id)
    assert group["counts"]["failed"] == 1 and group["counts"]["succeeded"] == 0

    failed_only = client.get("/api/v1/history?state=failed&page_size=50").json()["data"]
    group = next(item for item in failed_only["groups"] if item["media_id"] == media_id)
    assert [record["id"] for record in group["records"]] == [second]

    searched = client.get("/api/v1/history?q=谷雨&page_size=50").json()["data"]
    assert any(item["media_id"] == media_id for item in searched["groups"])
    assert client.get("/api/v1/history?state=bogus").status_code == 422
