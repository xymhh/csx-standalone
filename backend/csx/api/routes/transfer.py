"""转存任务与历史 API（原 routes/resources.py 拆分）。"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.api.envelope import ok
from csx.api.routes.resource_common import _page, _raise
from csx.application.failure_label import failure_detail, failure_label
from csx.domain.task import TaskState, stage_label
from csx.infra.db import get_db
from csx.infra.models import (
    Account,
    DiscoveredResource,
    Episode,
    LibraryFile,
    ManualTransfer,
    MediaItem,
    Season,
    Subscription,
    TransferTask,
)
from csx.infra.task_runtime import transition_task

tasks = APIRouter(prefix="/tasks", tags=["tasks"])
history = APIRouter(prefix="/history", tags=["history"])


ACTIVE_TASK_STATES = ("queued", "running", "retry_wait", "dead_letter")
HISTORY_STATES = {"succeeded": "succeeded", "failed": "dead_letter", "skipped": "cancelled"}


def _json_payload(raw: str | None) -> dict:
    try:
        data = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _library_index(db: Session, media_ids: set[int]) -> dict[tuple[int, int, int], LibraryFile]:
    """(media_id, season, episode) → 已落库文件，后者覆盖前者（最新一条）。"""
    if not media_ids:
        return {}
    rows = db.execute(
        select(LibraryFile, Season.media_id, Season.season_number, Episode.episode_number)
        .join(Episode, Episode.id == LibraryFile.episode_id)
        .join(Season, Season.id == Episode.season_id)
        .where(Season.media_id.in_(media_ids))
        .order_by(LibraryFile.id)
    ).all()
    index: dict[tuple[int, int, int], LibraryFile] = {}
    for file_row, media_id, season_number, episode_number in rows:
        index[(media_id, season_number, episode_number)] = file_row
    return index


def _enrich_tasks(db: Session, rows: list[TransferTask]) -> list[dict]:
    """把任务补全成「业务视角」：片名、年份、集数、网盘、阶段、失败短标签。"""
    if not rows:
        return []
    task_ids = [row.id for row in rows]
    sub_ids = {row.subscription_id for row in rows if row.subscription_id}
    res_ids = {row.resource_id for row in rows if row.resource_id}
    manuals = {
        row.task_id: row
        for row in db.scalars(select(ManualTransfer).where(ManualTransfer.task_id.in_(task_ids)))
    }
    subscriptions = (
        {
            row.id: row
            for row in db.scalars(select(Subscription).where(Subscription.id.in_(sub_ids)))
        }
        if sub_ids
        else {}
    )
    resources = (
        {
            row.id: row
            for row in db.scalars(
                select(DiscoveredResource).where(DiscoveredResource.id.in_(res_ids))
            )
        }
        if res_ids
        else {}
    )
    account_ids = {manual.account_id for manual in manuals.values() if manual.account_id}
    accounts = (
        {row.id: row for row in db.scalars(select(Account).where(Account.id.in_(account_ids)))}
        if account_ids
        else {}
    )
    media_ids: set[int] = {
        subscription.media_id for subscription in subscriptions.values() if subscription.media_id
    } | {manual.media_id for manual in manuals.values() if manual.media_id}
    medias = (
        {row.id: row for row in db.scalars(select(MediaItem).where(MediaItem.id.in_(media_ids)))}
        if media_ids
        else {}
    )
    library = _library_index(db, media_ids)

    result: list[dict] = []
    for row in rows:
        subscription = subscriptions.get(row.subscription_id or -1)
        manual = manuals.get(row.id)
        resource = resources.get(row.resource_id or -1)
        payload = _json_payload(resource.payload if resource is not None else None)
        account = accounts.get(manual.account_id) if manual is not None else None
        media_id = (
            subscription.media_id
            if subscription is not None
            else (manual.media_id if manual is not None else None)
        )
        media = medias.get(media_id or -1)
        provider = (resource.provider if resource is not None else "") or (
            account.provider if account is not None else ""
        )
        season = _int_or_none(payload.get("season"))
        episode = _int_or_none(payload.get("episode"))
        if episode is None and manual is not None and media is not None:
            episode = 1
        if season is None and episode is not None and media is not None and media.type != "movie":
            season = 1
        file_row = library.get((media_id, season or 1, episode or 1)) if media_id else None
        if file_row is not None:
            season = season if season is not None else 1
            episode = episode if episode is not None else 1
        title = (media.title if media is not None else "") or ""
        display_name = str(payload.get("title") or "").strip()
        if not display_name and file_row is not None:
            display_name = str(file_row.path).rstrip("/").split("/")[-1]
        if not display_name:
            if season is not None and episode is not None:
                display_name = f"S{season:02d}E{episode:02d}"
            elif media is not None:
                display_name = title
            else:
                display_name = f"手动转存 #{row.id}"
        result.append(
            {
                "id": row.id,
                "subscription_id": row.subscription_id,
                "resource_id": row.resource_id,
                "idempotency_key": row.idempotency_key,
                "state": row.state,
                "stage": row.stage or "",
                "stage_label": stage_label(row.stage),
                "attempt": row.attempt,
                "next_retry_at": row.next_retry_at,
                "last_error": row.last_error,
                "failure_label": failure_label(row.last_error),
                "failure_detail": failure_detail(row.last_error),
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "media_id": media_id,
                "media_title": title,
                "media_year": media.year if media is not None else None,
                "media_type": media.type if media is not None else "",
                "poster_url": media.poster_url if media is not None else "",
                "season": season,
                "episode": episode,
                "provider": provider,
                "quality_bucket": (
                    (file_row.quality_bucket if file_row is not None else "")
                    or str(payload.get("quality_bucket") or "")
                ),
                "display_name": display_name,
                "file_path": file_row.path if file_row is not None else "",
                "size": file_row.size if file_row is not None else None,
                "landed": file_row is not None,
            }
        )
    return result


def _task_data(row: TransferTask) -> dict:
    return {
        "id": row.id,
        "subscription_id": row.subscription_id,
        "resource_id": row.resource_id,
        "idempotency_key": row.idempotency_key,
        "state": row.state,
        "stage": row.stage or "",
        "stage_label": stage_label(row.stage),
        "attempt": row.attempt,
        "next_retry_at": row.next_retry_at,
        "last_error": row.last_error,
        "failure_label": failure_label(row.last_error),
        "failure_detail": failure_detail(row.last_error),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@tasks.get("")
def list_tasks(
    state: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    """任务队列：默认只返回进行中的任务，历史记录走 /history。"""
    query = select(TransferTask)
    if state:
        if state not in ACTIVE_TASK_STATES:
            _raise(422, "INVALID_STATE", "任务状态无效")
        query = query.where(TransferTask.state == state)
    else:
        query = query.where(TransferTask.state.in_(ACTIVE_TASK_STATES))
    rows = _page(db, query.order_by(TransferTask.id.desc()), page, page_size)
    return ok(_enrich_tasks(db, list(rows)))


def _reset_task(db: Session, row: TransferTask) -> None:
    transition_task(db, row.id, TaskState.QUEUED)
    row.attempt = 0
    row.next_retry_at = None
    row.dead_letter = 0
    row.last_error = ""
    db.flush()


@tasks.post("/{task_id}/retry")
def retry_task(task_id: int, db: Session = Depends(get_db)):
    row = db.get(TransferTask, task_id)
    if row is None:
        _raise(404, "TASK_NOT_FOUND", "任务不存在")
    if row.state not in {"retry_wait", "dead_letter"}:
        _raise(409, "TASK_NOT_RETRYABLE", "仅 retry_wait 或 dead_letter 任务可重试")
    _reset_task(db, row)
    db.commit()
    return ok(_task_data(row))


@tasks.post("/{task_id}/cancel")
def cancel_task(task_id: int, db: Session = Depends(get_db)):
    row = db.get(TransferTask, task_id)
    if row is None:
        _raise(404, "TASK_NOT_FOUND", "任务不存在")
    if row.state != "queued":
        _raise(409, "TASK_NOT_CANCELLABLE", "仅排队中的任务可取消")
    transition_task(db, task_id, TaskState.CANCELLED)
    db.commit()
    return ok(_task_data(row))


def _history_group_key(item: dict) -> str:
    if item.get("media_id"):
        return f"media:{item['media_id']}"
    if item.get("subscription_id"):
        return f"sub:{item['subscription_id']}"
    return f"task:{item['id']}"


def _group_history(items: list[dict]) -> list[dict]:
    """按媒体聚合历史记录，组内保留逐集明细（CS 插件的「汇总 + 展开」）。"""
    buckets: dict[str, dict] = {}
    for item in items:
        key = _history_group_key(item)
        group = buckets.get(key)
        if group is None:
            group = {
                "key": key,
                "media_id": item.get("media_id"),
                "title": item.get("media_title") or "",
                "year": item.get("media_year"),
                "type": item.get("media_type") or "",
                "poster_url": item.get("poster_url") or "",
                "counts": {"succeeded": 0, "failed": 0, "skipped": 0},
                "failure_labels": {},
                "providers": [],
                "total_size": 0,
                "latest_at": item.get("updated_at"),
                "records": [],
            }
            buckets[key] = group
        state = item.get("state")
        if state == "succeeded":
            group["counts"]["succeeded"] += 1
        elif state == "cancelled":
            group["counts"]["skipped"] += 1
        else:
            group["counts"]["failed"] += 1
        label = item.get("failure_label") or ""
        if label and state != "succeeded":
            group["failure_labels"][label] = group["failure_labels"].get(label, 0) + 1
        provider = item.get("provider") or ""
        if provider and provider not in group["providers"]:
            group["providers"].append(provider)
        group["total_size"] += int(item.get("size") or 0)
        if item.get("updated_at") and (
            group["latest_at"] is None or item["updated_at"] > group["latest_at"]
        ):
            group["latest_at"] = item["updated_at"]
        if not group["title"]:
            group["title"] = item.get("media_title") or item.get("display_name") or ""
        group["records"].append(item)

    groups = []
    for group in buckets.values():
        labels = sorted(group.pop("failure_labels").items(), key=lambda pair: -pair[1])
        group["failure_labels"] = [
            {"label": label, "count": count} for label, count in labels if label
        ][:2]
        if not group["title"]:
            group["title"] = "手动转存"
        group["records"].sort(
            key=lambda record: (
                record.get("season") or 0,
                record.get("episode") or 0,
                record.get("updated_at") or datetime.min,
            )
        )
        groups.append(group)
    groups.sort(key=lambda group: group["latest_at"] or datetime.min, reverse=True)
    return groups


@history.get("")
def list_history(
    provider: str | None = None,
    state: str | None = None,
    q: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    if state and state not in {*HISTORY_STATES, "all"}:
        _raise(422, "INVALID_STATE", "历史状态无效")
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    query = select(TransferTask).where(TransferTask.state.in_(HISTORY_STATES.values()))
    if state and state in HISTORY_STATES:
        query = query.where(TransferTask.state == HISTORY_STATES[state])
    if start:
        query = query.where(TransferTask.updated_at >= start)
    if end:
        query = query.where(TransferTask.updated_at <= end)
    rows = list(db.scalars(query.order_by(TransferTask.updated_at.desc())).all())
    items = _enrich_tasks(db, rows)

    provider_options: list[str] = []
    for item in items:
        provider_value = item.get("provider") or ""
        if provider_value and provider_value not in provider_options:
            provider_options.append(provider_value)

    if provider:
        items = [item for item in items if (item.get("provider") or "") == provider]
    keyword = (q or "").strip().lower()
    if keyword:
        items = [
            item
            for item in items
            if keyword in str(item.get("media_title") or "").lower()
            or keyword in str(item.get("display_name") or "").lower()
        ]

    groups = _group_history(items)
    total = len(groups)
    offset = (page - 1) * page_size
    return ok(
        {
            "groups": groups[offset : offset + page_size],
            "total": total,
            "records_total": len(items),
            "page": page,
            "page_size": page_size,
            "filter_options": {"providers": provider_options},
        }
    )


@history.post("/retry_failed")
def retry_all_failed(db: Session = Depends(get_db)):
    """一键重试全部失败任务（CS 插件历史页的「重试全部失败」）。"""
    rows = list(db.scalars(select(TransferTask).where(TransferTask.state == "dead_letter")).all())
    for row in rows:
        _reset_task(db, row)
    db.commit()
    return ok({"retried": len(rows)})


@history.post("/retry_batch")
def retry_batch(task_ids: list[int], db: Session = Depends(get_db)):
    if not task_ids or len(task_ids) > 100:
        _raise(422, "VALIDATION_ERROR", "task_ids 数量须为 1 到 100")
    updated = []
    for task_id in dict.fromkeys(task_ids):
        row = db.get(TransferTask, task_id)
        if row is None or row.state != "dead_letter":
            continue
        _reset_task(db, row)
        updated.append(task_id)
    db.commit()
    return ok({"retried": updated})
