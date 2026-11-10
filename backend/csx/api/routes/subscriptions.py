"""订阅与候选资源 API（原 routes/resources.py 拆分）。"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.adapters.library import SqlAlchemyLibraryRepository
from csx.api.envelope import ok
from csx.api.routes.resource_common import _page, _raise
from csx.application import auto_search
from csx.domain.resource import idempotency_key
from csx.domain.subscription import SubscriptionScope
from csx.domain.upgrade import UpgradeAction, decide_upgrade
from csx.infra.db import get_db
from csx.infra.models import (
    DiscoveredResource,
    Episode,
    MediaItem,
    Season,
    Subscription,
)
from csx.infra.task_runtime import create_or_get_task

subscriptions = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
candidates = APIRouter(prefix="/candidates", tags=["candidates"])


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


class CandidateIn(BaseModel):
    subscription_id: int
    provider: str
    share_url: str
    password: str = ""
    season: int = 1
    episode: int = 1
    quality_bucket: str = "1080p"


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
        media = db.scalar(
            select(MediaItem).where(MediaItem.title == title, MediaItem.type == m_type)
        )
        if media is None:
            fake_tmdb = body.tmdb_id
            poster_url = None
            overview = ""

            # 尝试通过 TMDB 补充官方海报与简介
            from csx.adapters.media.tmdb import TmdbClient

            if body.tmdb_id and body.tmdb_id > 0:
                detail = TmdbClient.get_detail(m_type, body.tmdb_id)
                if detail:
                    poster_url = detail.get("poster_url")
                    overview = detail.get("overview") or ""
            elif title:
                search_res = TmdbClient.search(title)
                if search_res:
                    first = search_res[0]
                    poster_url = first.get("poster_url")
                    overview = first.get("overview") or ""
                    if not fake_tmdb and first.get("id"):
                        fake_tmdb = first.get("id")

            if not fake_tmdb:
                import random

                while True:
                    cand = -random.randint(10000, 999999999)
                    if not db.scalar(select(MediaItem).where(MediaItem.tmdb_id == cand)):
                        fake_tmdb = cand
                        break

            media = MediaItem(
                title=title,
                type=m_type,
                year=body.year,
                tmdb_id=fake_tmdb,
                poster_url=poster_url,
                overview=overview,
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
def sync_subscription(subscription_id: int, db: Session = Depends(get_db)):
    """立即为这部订阅跑一轮真实搜源，命中缺失集时落候选并按配置自动转存。"""
    row = db.get(Subscription, subscription_id)
    if row is None:
        _raise(404, "SUBSCRIPTION_NOT_FOUND", "订阅不存在")
    config = auto_search.load_settings(db)
    result = auto_search.search_subscription(
        db,
        row,
        limit=int(config["per_subscription_limit"]),
        auto_transfer=bool(config["auto_transfer"]),
    )
    tasks = list(result.get("tasks") or [])
    candidates = int(result.get("candidates") or 0)
    if not result.get("ok", True):
        message = str(result.get("message") or "搜源失败")
    elif candidates == 0:
        message = "已搜索，暂无新的可转存资源"
    elif tasks:
        message = f"搜到 {candidates} 条新资源，已自动转存 {len(tasks)} 个"
    else:
        message = f"搜到 {candidates} 条新资源，已加入待选"
    return ok(
        {
            "triggered": True,
            "task_id": str(tasks[0]) if tasks else "",
            "message": message,
            "candidates": candidates,
            "tasks": tasks,
            "skipped": result.get("skipped") or {},
        }
    )


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


@candidates.post("")
def create_candidate(body: CandidateIn, db: Session = Depends(get_db)):
    """手动登记一条分享链接，作为候选进入转存流程。"""
    subscription = db.get(Subscription, body.subscription_id)
    if subscription is None:
        _raise(404, "SUBSCRIPTION_NOT_FOUND", "订阅不存在")
    if body.provider not in {"115", "quark"}:
        _raise(422, "UNSUPPORTED_PROVIDER", "暂不支持此网盘")
    share_url = body.share_url.strip()
    if not share_url.startswith(("http://", "https://")):
        _raise(422, "SHARE_URL_INVALID", "分享链接格式不正确")
    digest = hashlib.sha256(
        f"{body.provider}|{share_url}|{body.season}|{body.episode}".encode()
    ).hexdigest()
    dedup = f"manual:{subscription.id}:{digest[:32]}"
    row = db.scalars(
        select(DiscoveredResource).where(DiscoveredResource.dedup_key == dedup)
    ).first()
    if row is None:
        row = DiscoveredResource(
            subscription_id=subscription.id,
            provider=body.provider,
            share_url=share_url,
            dedup_key=dedup,
            state="new",
            payload=json.dumps(
                {
                    "season": body.season,
                    "episode": body.episode,
                    "quality_bucket": body.quality_bucket,
                    "password": body.password,
                    "manual": True,
                },
                ensure_ascii=False,
            ),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return ok({"candidate_id": row.id, "state": row.state})


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
