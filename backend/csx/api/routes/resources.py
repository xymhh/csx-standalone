"""Authenticated resource APIs for subscriptions, jobs, settings and accounts."""

from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.adapters.drive.registry import DriveRegistry
from csx.adapters.library import SqlAlchemyLibraryRepository
from csx.adapters.media.emby import server_clients
from csx.api.envelope import ok
from csx.domain.resource import idempotency_key
from csx.domain.subscription import SubscriptionScope
from csx.domain.task import TaskState
from csx.domain.upgrade import UpgradeAction, decide_upgrade
from csx.infra.credentials import encrypt_credential
from csx.infra.db import SessionLocal, get_db
from csx.infra.drive_runtime import drive_for
from csx.infra.events import event_bus
from csx.infra.models import (
    Account,
    DiscoveredResource,
    Episode,
    LibraryFile,
    MediaItem,
    Season,
    Setting,
    Subscription,
    TransferTask,
)
from csx.infra.settings import settings
from csx.infra.task_runtime import create_or_get_task, transition_task

subscriptions = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
progress = APIRouter(prefix="/progress", tags=["progress"])
candidates = APIRouter(prefix="/candidates", tags=["candidates"])
tasks = APIRouter(prefix="/tasks", tags=["tasks"])
history = APIRouter(prefix="/history", tags=["history"])
library = APIRouter(prefix="/library", tags=["library"])
settings_api = APIRouter(prefix="/settings", tags=["settings"])
accounts = APIRouter(prefix="/accounts", tags=["accounts"])
doctor = APIRouter(prefix="/doctor", tags=["doctor"])
events = APIRouter(prefix="/events", tags=["events"])
SECTIONS = {"baseline", "sources", "transfer", "strm", "notify", "advanced"}
HEARTBEAT_SECONDS = 15


def _raise(status: int, code: str, message: str) -> None:
    raise HTTPException(status, detail={"code": code, "message": message})


def _page(db: Session, query, page: int, page_size: int):
    if page < 1 or page_size < 1 or page_size > 200:
        _raise(422, "VALIDATION_ERROR", "分页参数无效")
    result = db.execute(query.offset((page - 1) * page_size).limit(page_size))
    if len(query.column_descriptions) == 1:
        return result.scalars().all()
    return result.all()


class SubscriptionIn(BaseModel):
    media_id: int | None = Field(default=None, gt=0)
    tmdb_id: int | None = Field(default=None, gt=0)
    title: str | None = None
    media_type: str = Field(default="tv")
    year: int | None = None
    season_number: int = Field(default=1, ge=1)
    episode_count: int = Field(default=12, ge=1)
    scope: dict[str, Any] = Field(default_factory=dict)
    quality_pref: dict[str, Any] | str = Field(default_factory=dict)
    source: str = Field(default="manual", min_length=1, max_length=64)


class SubscriptionPatch(BaseModel):
    state: str | None = None
    scope: dict[str, Any] | None = None
    quality_pref: dict[str, Any] | str | None = None


class AccountIn(BaseModel):
    provider: str = Field(min_length=1, max_length=32)
    credential: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=128)


class AccountPatch(BaseModel):
    credential: str | None = Field(default=None, min_length=1)
    name: str | None = Field(default=None, min_length=1, max_length=128)


class QrcodeStartRequest(BaseModel):
    provider: Literal["115", "quark"]


class QrcodeCheckRequest(BaseModel):
    provider: Literal["115", "quark"]
    token_data: dict[str, Any]
    name: str = Field(default="我的115账号", min_length=1, max_length=128)
    auto_save: bool = True


def _quality_json(value: dict | str) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


def _subscription_data(row: Subscription, media: MediaItem | None = None) -> dict:
    result = {
        "id": row.id,
        "media_id": row.media_id,
        "scope": json.loads(row.scope or "{}"),
        "quality_pref": json.loads(row.quality_pref or "{}"),
        "state": row.state,
        "source": row.source,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
    if media is not None:
        result["media"] = {"tmdb_id": media.tmdb_id, "title": media.title, "type": media.type}
    return result


@subscriptions.get("")
def list_subscriptions(
    state: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    query = select(Subscription, MediaItem).join(MediaItem, Subscription.media_id == MediaItem.id)
    if state is not None:
        if state not in {"active", "paused"}:
            _raise(422, "INVALID_STATE", "订阅状态无效")
        query = query.where(Subscription.state == state)
    if keyword:
        query = query.where(MediaItem.title.contains(keyword))
    rows = _page(db, query.order_by(Subscription.id), page, page_size)
    return ok([_subscription_data(sub, media) for sub, media in rows])


@subscriptions.post("")
def create_subscription(body: SubscriptionIn, db: Session = Depends(get_db)):
    media = db.get(MediaItem, body.media_id) if body.media_id else None
    if media is None and body.tmdb_id:
        media = db.scalar(select(MediaItem).where(MediaItem.tmdb_id == body.tmdb_id))

    # 若媒体未入库，根据片名或 TMDB ID 自动建立媒体、季与集记录
    if media is None:
        title = (body.title or "").strip()
        if not title:
            if body.tmdb_id:
                title = f"影视 TMDB-{body.tmdb_id}"
            else:
                _raise(400, "TITLE_REQUIRED", "请提供影视片名或有效的媒体编号")

        m_type = "movie" if body.media_type == "movie" else "tv"
        media = MediaItem(
            title=title,
            type=m_type,
            year=body.year,
            tmdb_id=body.tmdb_id,
        )
        db.add(media)
        db.flush()

        if m_type == "tv":
            season_num = max(1, body.season_number)
            ep_count = max(1, body.episode_count)
            season = Season(media_id=media.id, season_number=season_num, episode_count=ep_count)
            db.add(season)
            db.flush()
            for ep_i in range(1, ep_count + 1):
                db.add(Episode(season_id=season.id, episode_number=ep_i, title=f"第 {ep_i} 集"))
        else:
            season = Season(media_id=media.id, season_number=1, episode_count=1)
            db.add(season)
            db.flush()
            db.add(Episode(season_id=season.id, episode_number=1, title="正片"))
        db.flush()

    row = Subscription(
        media_id=media.id,
        scope=SubscriptionScope.from_json(body.scope).to_json(),
        quality_pref=_quality_json(body.quality_pref),
        source=body.source,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(_subscription_data(row, media))


@subscriptions.get("/{subscription_id}")
def get_subscription(subscription_id: int, db: Session = Depends(get_db)):
    row = db.get(Subscription, subscription_id)
    if row is None:
        _raise(404, "SUBSCRIPTION_NOT_FOUND", "订阅不存在")
    result = _subscription_data(row, db.get(MediaItem, row.media_id))
    result["matches"] = [
        {"id": item.id, "provider": item.provider, "state": item.state}
        for item in db.scalars(
            select(DiscoveredResource).where(DiscoveredResource.subscription_id == subscription_id)
        )
    ]
    return ok(result)


@subscriptions.patch("/{subscription_id}")
def patch_subscription(
    subscription_id: int, body: SubscriptionPatch, db: Session = Depends(get_db)
):
    row = db.get(Subscription, subscription_id)
    if row is None:
        _raise(404, "SUBSCRIPTION_NOT_FOUND", "订阅不存在")
    changes = body.model_dump(exclude_unset=True)
    if "state" in changes:
        if changes["state"] not in {"active", "paused"}:
            _raise(422, "INVALID_STATE", "状态只能为 active 或 paused")
        row.state = changes["state"]
    if "scope" in changes:
        row.scope = SubscriptionScope.from_json(changes["scope"]).to_json()
    if "quality_pref" in changes and changes["quality_pref"] is not None:
        row.quality_pref = _quality_json(changes["quality_pref"])
    row.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return ok(_subscription_data(row, db.get(MediaItem, row.media_id)))


@subscriptions.delete("/{subscription_id}")
def delete_subscription(subscription_id: int, db: Session = Depends(get_db)):
    row = db.get(Subscription, subscription_id)
    if row is None:
        _raise(404, "SUBSCRIPTION_NOT_FOUND", "订阅不存在")
    row.state = "deleted"
    row.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return ok({"deleted": True})


@subscriptions.post("/{subscription_id}/sync")
async def sync_subscription(subscription_id: int, db: Session = Depends(get_db)):
    row = db.get(Subscription, subscription_id)
    if row is None:
        _raise(404, "SUBSCRIPTION_NOT_FOUND", "订阅不存在")
    token = uuid.uuid4().hex
    sample = DiscoveredResource(
        subscription_id=row.id,
        provider="pending",
        share_url="",
        dedup_key=f"sync:{row.id}:{token}",
        state="discovered",
        payload=json.dumps({"triggered": True, "message": "已触发同步"}, ensure_ascii=False),
    )
    db.add(sample)
    db.commit()
    db.refresh(sample)
    await event_bus.publish("candidate_found", {"candidate_id": sample.id})
    return ok({"triggered": True, "task_id": str(sample.id), "message": "已触发同步"})


def _resource_data(row: DiscoveredResource) -> dict:
    return {
        "id": row.id,
        "subscription_id": row.subscription_id,
        "provider": row.provider,
        "share_url": row.share_url,
        "state": "discovered" if row.state == "new" else row.state,
        "score": row.score,
        "payload": json.loads(row.payload or "{}"),
        "created_at": row.created_at,
    }


@candidates.get("")
def list_candidates(
    subscription_id: int | None = None,
    state: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    query = select(DiscoveredResource)
    if subscription_id is not None:
        query = query.where(DiscoveredResource.subscription_id == subscription_id)
    if state is not None:
        if state not in {"discovered", "accepted", "ignored"}:
            _raise(422, "INVALID_STATE", "候选状态无效")
        if state == "discovered":
            query = query.where(DiscoveredResource.state.in_({"new", "discovered"}))
        else:
            query = query.where(DiscoveredResource.state == state)
    rows = _page(db, query.order_by(DiscoveredResource.id.desc()), page, page_size)
    return ok([_resource_data(row) for row in rows])


@candidates.post("/{candidate_id}/accept")
def accept_candidate(candidate_id: int, db: Session = Depends(get_db)):
    row = db.get(DiscoveredResource, candidate_id)
    if row is None:
        _raise(404, "CANDIDATE_NOT_FOUND", "候选不存在")
    if row.state not in {"new", "discovered"}:
        _raise(409, "CANDIDATE_NOT_AVAILABLE", "候选已处理")
    payload = json.loads(row.payload or "{}")
    season = int(payload.get("season", 1))
    episode = int(payload.get("episode", 1))
    bucket = str(payload.get("quality_bucket", "sd"))
    subscription = db.get(Subscription, row.subscription_id)
    existing = (
        SqlAlchemyLibraryRepository(db).get_episode_file(
            media_id=subscription.media_id, season=season, episode=episode
        )
        if subscription
        else None
    )
    quality_pref = json.loads(subscription.quality_pref or "{}") if subscription else {}
    upgrade_enabled = (
        bool(quality_pref.get("upgrade_enabled", True)) if isinstance(quality_pref, dict) else True
    )
    decision = (
        decide_upgrade(existing.get("quality_bucket"), bucket, upgrade_enabled=upgrade_enabled)
        if existing
        else None
    )
    if decision and decision.action is not UpgradeAction.UPGRADE:
        row.state = "ignored_low_quality"
        db.commit()
        return ok(
            {
                "candidate_id": row.id,
                "state": "ignored_low_quality",
                "existing_bucket": decision.existing_bucket,
                "candidate_bucket": decision.candidate_bucket,
            }
        )
    key = row.idempotency_key or idempotency_key(
        row.provider, row.share_url, season, episode, bucket
    )
    task_id, _created = create_or_get_task(
        db, key, subscription_id=row.subscription_id, resource_id=row.id
    )
    row.idempotency_key = key
    row.state = "accepted"
    db.commit()
    return ok(
        {
            "candidate_id": row.id,
            "task_id": task_id,
            "state": "queued",
            "is_upgrade": bool(decision and decision.is_upgrade),
        }
    )


@candidates.post("/{candidate_id}/ignore")
def ignore_candidate(candidate_id: int, db: Session = Depends(get_db)):
    row = db.get(DiscoveredResource, candidate_id)
    if row is None:
        _raise(404, "CANDIDATE_NOT_FOUND", "候选不存在")
    if row.state == "accepted":
        _raise(409, "CANDIDATE_ALREADY_ACCEPTED", "已采纳的候选不能忽略")
    row.state = "ignored"
    db.commit()
    return ok({"candidate_id": row.id, "state": row.state})


def _task_data(row: TransferTask) -> dict:
    return {
        "id": row.id,
        "subscription_id": row.subscription_id,
        "resource_id": row.resource_id,
        "idempotency_key": row.idempotency_key,
        "state": row.state,
        "attempt": row.attempt,
        "next_retry_at": row.next_retry_at,
        "last_error": row.last_error,
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
    query = select(TransferTask)
    if state:
        if state not in {"queued", "running", "retry_wait", "dead_letter"}:
            _raise(422, "INVALID_STATE", "任务状态无效")
        query = query.where(TransferTask.state == state)
    rows = _page(db, query.order_by(TransferTask.id.desc()), page, page_size)
    return ok([_task_data(row) for row in rows])


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


@history.get("")
def list_history(
    provider: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    query = select(TransferTask).where(TransferTask.state.in_({"succeeded", "dead_letter"}))
    if provider:
        query = query.join(
            DiscoveredResource,
            TransferTask.resource_id == DiscoveredResource.id,
        ).where(DiscoveredResource.provider == provider)
    if start:
        query = query.where(TransferTask.updated_at >= start)
    if end:
        query = query.where(TransferTask.updated_at <= end)
    rows = _page(db, query.order_by(TransferTask.updated_at.desc()), page, page_size)
    return ok([_task_data(row) for row in rows])


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


@progress.get("")
def progress_overview(db: Session = Depends(get_db)):
    media_rows = db.scalars(select(MediaItem).order_by(MediaItem.id)).all()
    return ok([_media_progress(db, media) for media in media_rows])


def _media_progress(db: Session, media: MediaItem) -> dict:
    seasons = db.scalars(select(Season).where(Season.media_id == media.id)).all()
    aired = 0
    owned = 0
    missing = []
    matrix = []
    today = datetime.now(UTC).date()
    for season in seasons:
        episodes = db.scalars(
            select(Episode).where(Episode.season_id == season.id).order_by(Episode.episode_number)
        ).all()
        entries = []
        for episode in episodes:
            file_row = db.scalar(select(LibraryFile).where(LibraryFile.episode_id == episode.id))
            has_aired = episode.air_date is None or episode.air_date <= today
            aired += int(has_aired)
            owned += int(file_row is not None)
            if has_aired and file_row is None:
                missing.append({"season": season.season_number, "episode": episode.episode_number})
            entries.append(
                {
                    "episode": episode.episode_number,
                    "title": episode.title,
                    "air_date": episode.air_date,
                    "aired": has_aired,
                    "owned": file_row is not None,
                    "file": (
                        {
                            "file_id": file_row.id,
                            "path": file_row.path,
                            "size": file_row.size,
                            "sha1": file_row.sha1,
                            "quality_bucket": file_row.quality_bucket,
                            "created_at": file_row.created_at,
                        }
                        if file_row
                        else None
                    ),
                }
            )
        matrix.append({"season": season.season_number, "episodes": entries})
    return {
        "media_id": media.id,
        "title": media.title,
        "type": media.type,
        "year": media.year,
        "overview": media.overview,
        "poster_url": media.poster_url,
        "rating": getattr(media, "rating", None),
        "aired_count": aired,
        "owned_count": owned,
        "missing": missing,
        "seasons": matrix,
    }


@progress.get("/{media_id}")
def media_progress(media_id: int, db: Session = Depends(get_db)):
    media = db.get(MediaItem, media_id)
    if media is None:
        _raise(404, "MEDIA_NOT_FOUND", "媒体不存在")
    return ok(_media_progress(db, media))


@library.get("/files")
def library_files(
    media_id: int | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    query = (
        select(LibraryFile, Episode, Season)
        .join(Episode, LibraryFile.episode_id == Episode.id)
        .join(Season, Episode.season_id == Season.id)
    )
    if media_id is not None:
        query = query.where(Season.media_id == media_id)
    rows = _page(db, query.order_by(LibraryFile.id.desc()), page, page_size)
    return ok(
        [
            {
                "id": file.id,
                "media_id": season.media_id,
                "season": season.season_number,
                "episode": episode.episode_number,
                "path": file.path,
                "size": file.size,
                "sha1": file.sha1,
                "quality_bucket": file.quality_bucket,
            }
            for file, episode, season in rows
        ]
    )


@library.get("/servers")
def library_servers(db: Session = Depends(get_db)):
    advanced = {}
    for row in db.scalars(select(Setting).where(Setting.key.like("advanced.%"))):
        advanced[row.key.split(".", 1)[1]] = json.loads(row.value)
    clients = {client.provider: client for client in server_clients(advanced)}
    result = []
    for provider in ("emby", "jellyfin"):
        client = clients.get(provider)
        if client is None:
            result.append({"provider": provider, "configured": False, "valid": None})
            continue
        try:
            info = client.probe()
            result.append(
                {
                    "provider": provider,
                    "configured": True,
                    "valid": True,
                    "name": info.name,
                    "version": info.version,
                }
            )
        except Exception as error:
            result.append(
                {
                    "provider": provider,
                    "configured": True,
                    "valid": False,
                    "message": str(error),
                }
            )
        finally:
            client.close()
    return ok(result)


@settings_api.get("")
def all_settings(db: Session = Depends(get_db)):
    values = {section: {} for section in sorted(SECTIONS)}
    for row in db.scalars(select(Setting)):
        section, separator, key = row.key.partition(".")
        if separator and section in SECTIONS:
            values[section][key] = json.loads(row.value)
    return ok(values)


@settings_api.get("/{section}")
def get_settings(section: str, db: Session = Depends(get_db)):
    if section not in SECTIONS:
        _raise(404, "INVALID_SECTION", "设置分组不存在")
    values = {}
    for row in db.scalars(select(Setting).where(Setting.key.like(f"{section}.%"))):
        values[row.key.split(".", 1)[1]] = json.loads(row.value)
    return ok(values)


@settings_api.put("/{section}")
def put_settings(section: str, body: dict[str, Any], db: Session = Depends(get_db)):
    if section not in SECTIONS:
        _raise(404, "INVALID_SECTION", "设置分组不存在")
    for key, value in body.items():
        if not key or "." in key:
            _raise(422, "INVALID_SETTING_KEY", "配置项名称无效")
        setting = db.get(Setting, f"{section}.{key}")
        if setting is None:
            setting = Setting(key=f"{section}.{key}", value=json.dumps(value, ensure_ascii=False))
            db.add(setting)
        else:
            setting.value = json.dumps(value, ensure_ascii=False)
            setting.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return get_settings(section, db)


def _drive_for(request: Request, db: Session, provider: str):
    drive = drive_for(db, provider, getattr(request.app.state, "drives", {}))
    if drive is None:
        _raise(404, "ACCOUNT_NOT_FOUND", f"未配置 {provider} 网盘账号")
    return drive


@settings_api.post("/test/{provider}")
def test_provider(provider: str, request: Request, db: Session = Depends(get_db)):
    try:
        _drive_for(request, db, provider.lower()).list_dir("/")
        return ok({"valid": True, "provider": provider, "message": "连通正常"})
    except Exception as error:
        return ok({"valid": False, "provider": provider, "message": str(error)})


def _account_data(row: Account) -> dict:
    return {
        "id": row.id,
        "provider": row.provider,
        "name": row.name,
        "has_credential": bool(row.credential),
        "masked": "***" if row.credential else "",
    }


@accounts.post("/qrcode/start")
def start_account_qrcode(body: QrcodeStartRequest):
    try:
        return ok(DriveRegistry.create_qrcode(body.provider))
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "QRCODE_START_FAILED", "message": str(error)},
        ) from error


@accounts.post("/qrcode/check")
def check_account_qrcode(
    body: QrcodeCheckRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        result = DriveRegistry.check_qrcode(body.provider, body.token_data)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "QRCODE_CHECK_FAILED", "message": str(error)},
        ) from error

    status = result["status"]
    account_data = None
    if status == "success":
        cookie = result.get("cookie")
        if not cookie:
            raise HTTPException(
                status_code=502,
                detail={"code": "QRCODE_COOKIE_MISSING", "message": "扫码成功但未获得账号凭据"},
            )
        if body.auto_save:
            if not body.name.strip():
                _raise(422, "INVALID_ACCOUNT_NAME", "账号备注名称不能为空")
            if db.scalar(select(Account).where(Account.provider == body.provider)) is not None:
                _raise(409, "ACCOUNT_EXISTS", "该网盘类型已有绑定账号，请先删除或更换现有账号")
            try:
                encrypted = encrypt_credential(cookie)
            except RuntimeError as error:
                _raise(503, "SECRET_KEY_REQUIRED", str(error))
            account = Account(provider=body.provider, name=body.name.strip(), credential=encrypted)
            db.add(account)
            db.commit()
            db.refresh(account)
            account_data = _account_data(account)
            getattr(request.app.state, "drives", {}).pop(body.provider, None)

    return ok(
        {
            "status": status,
            "message": "绑定成功" if status == "success" and body.auto_save else result["message"],
            "account": account_data,
        }
    )


@accounts.get("")
def list_accounts(db: Session = Depends(get_db)):
    rows = db.scalars(select(Account).order_by(Account.id))
    return ok([_account_data(row) for row in rows])


@accounts.post("")
def create_account(body: AccountIn, db: Session = Depends(get_db)):
    provider = body.provider.lower()
    if provider not in {"115", "quark"}:
        _raise(422, "UNSUPPORTED_PROVIDER", "目前支持 115 和 quark")
    if db.scalar(select(Account).where(Account.provider == provider)) is not None:
        _raise(409, "ACCOUNT_EXISTS", "该网盘账号已存在")
    try:
        credential = encrypt_credential(body.credential)
    except RuntimeError as error:
        _raise(503, "SECRET_KEY_REQUIRED", str(error))
    row = Account(provider=provider, credential=credential, name=body.name)
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(_account_data(row))


@accounts.patch("/{account_id}")
def update_account(
    account_id: int,
    body: AccountPatch,
    request: Request,
    db: Session = Depends(get_db),
):
    row = db.get(Account, account_id)
    if row is None:
        _raise(404, "ACCOUNT_NOT_FOUND", "账号不存在")
    values = body.model_dump(exclude_unset=True)
    if values.get("name") is not None:
        row.name = values["name"]
    if values.get("credential") is not None:
        try:
            row.credential = encrypt_credential(values["credential"])
        except RuntimeError as error:
            _raise(503, "SECRET_KEY_REQUIRED", str(error))
    db.commit()
    if values.get("credential") is not None:
        getattr(request.app.state, "drives", {}).pop(row.provider, None)
    return ok(_account_data(row))


@accounts.delete("/{account_id}")
def delete_account(account_id: int, request: Request, db: Session = Depends(get_db)):
    row = db.get(Account, account_id)
    if row is None:
        _raise(404, "ACCOUNT_NOT_FOUND", "账号不存在")
    provider = row.provider
    db.delete(row)
    db.commit()
    getattr(request.app.state, "drives", {}).pop(provider, None)
    return ok({"deleted": True})


@accounts.post("/{account_id}/test")
def test_account(account_id: int, request: Request, db: Session = Depends(get_db)):
    row = db.get(Account, account_id)
    if row is None:
        _raise(404, "ACCOUNT_NOT_FOUND", "账号不存在")
    try:
        _drive_for(request, db, row.provider).list_dir("/")
        return ok({"valid": True, "provider": row.provider, "message": "连通正常"})
    except Exception as error:
        return ok({"valid": False, "provider": row.provider, "message": str(error)})


@doctor.get("")
def diagnose(request: Request):
    db_ok = False
    db_error = ""
    db_size = 0
    try:
        with SessionLocal() as db:
            db.execute(select(1))
            db_ok = True
        db_path = settings.data_dir / "csx.db"
        db_size = db_path.stat().st_size if db_path.exists() else 0
    except Exception as error:
        db_error = str(error)
    data_path = Path(settings.data_dir)
    try:
        disk = shutil.disk_usage(data_path)
        writable = data_path.is_dir() and bool(data_path.stat().st_mode & 0o222)
        disk_result = {"total": disk.total, "free": disk.free, "writable": writable}
    except OSError as error:
        disk_result = {"error": str(error), "writable": False}
    scheduler = getattr(request.app.state, "scheduler", None)
    account_checks = []
    try:
        with SessionLocal() as db:
            for account in db.scalars(select(Account)):
                drive = getattr(request.app.state, "drives", {}).get(account.provider)
                if drive is None:
                    account_checks.append(
                        {"provider": account.provider, "configured": True, "valid": False}
                    )
                    continue
                try:
                    drive.list_dir("/")
                    valid, message = True, ""
                except Exception as exc:
                    valid = False
                    message = str(exc)
                account_checks.append(
                    {
                        "provider": account.provider,
                        "configured": True,
                        "valid": valid,
                        "message": message,
                        "quota": json.loads(account.quota_state or "{}"),
                    }
                )
    except Exception as error:
        account_checks = [{"error": str(error)}]
    return ok(
        {
            "database": {"ok": db_ok, "size_bytes": db_size, "error": db_error},
            "accounts": account_checks,
            "scheduler": {
                "running": bool(scheduler and scheduler.running),
                "active_workers": scheduler.active_workers if scheduler else 0,
                "waiting_queue_depth": scheduler.waiting_queue_depth if scheduler else 0,
            },
            "disk": disk_result,
        }
    )


@events.get("")
async def event_stream():
    async def generate():
        async with event_bus.subscribe() as queue:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except TimeoutError:
                    event = {"type": "heartbeat", "data": {"at": datetime.now(UTC).isoformat()}}
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )
