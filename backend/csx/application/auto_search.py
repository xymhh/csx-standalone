"""订阅自动搜源：定时为每部追剧在各搜索渠道找资源，命中即建候选/转存任务。

对应 CS 插件「订阅搜索 + 自动转存」那条链路，搜索层复用
``adapters.search.executor``（后台已配置的全部渠道），候选与任务复用
``discovered_resource`` / ``transfer_task`` 既有结构，不新造一套。
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.adapters.db.repositories import SqlAlchemyTaskRepository
from csx.adapters.search import executor
from csx.domain.media import EpisodeKey
from csx.domain.naming import parse_episode_from_name
from csx.domain.resource import BUCKET_ORDER, dedup_key, idempotency_key, score
from csx.domain.subscription import SubscriptionScope
from csx.infra.log import logger
from csx.infra.models import (
    DiscoveredResource,
    Episode,
    LibraryFile,
    MediaItem,
    Season,
    Setting,
    Subscription,
)

SETTING_KEY = "auto_search"
LAST_KEY_PREFIX = "auto_search.last."
DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "interval_hours": 6,
    "auto_transfer": True,
    "max_per_round": 10,
    "per_subscription_limit": 20,
}
_NORMALIZER = re.compile(r"[^\w\u3400-\u9fff]+", re.UNICODE)
_RESOLUTION = re.compile(r"(?i)(2160p|4k|1080p|720p|480p)")
_YEAR = re.compile(r"(19|20)\d{2}")
_TRANSFERABLE_PROVIDERS = {"115", "quark"}


def load_settings(db: Session) -> dict[str, Any]:
    row = db.get(Setting, SETTING_KEY)
    data = dict(DEFAULT_SETTINGS)
    if row is not None:
        try:
            stored = json.loads(row.value)
        except (TypeError, json.JSONDecodeError):
            stored = {}
        if isinstance(stored, dict):
            data.update({key: value for key, value in stored.items() if key in DEFAULT_SETTINGS})
    data["interval_hours"] = max(1, min(int(data["interval_hours"]), 168))
    data["max_per_round"] = max(1, min(int(data["max_per_round"]), 50))
    data["per_subscription_limit"] = max(5, min(int(data["per_subscription_limit"]), 50))
    data["enabled"] = bool(data["enabled"])
    data["auto_transfer"] = bool(data["auto_transfer"])
    return data


def save_settings(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    current = load_settings(db)
    for key in DEFAULT_SETTINGS:
        if key in payload and payload[key] is not None:
            current[key] = payload[key]
    row = db.get(Setting, SETTING_KEY)
    if row is None:
        db.add(Setting(key=SETTING_KEY, value=json.dumps(current, ensure_ascii=False)))
    else:
        row.value = json.dumps(current, ensure_ascii=False)
    db.commit()
    return load_settings(db)


def _last_run(db: Session, subscription_id: int) -> datetime | None:
    row = db.get(Setting, f"{LAST_KEY_PREFIX}{subscription_id}")
    if row is None:
        return None
    try:
        return datetime.fromisoformat(row.value)
    except (TypeError, ValueError):
        return None


def _mark_run(db: Session, subscription_id: int) -> None:
    value = datetime.now(UTC).isoformat(timespec="seconds")
    row = db.get(Setting, f"{LAST_KEY_PREFIX}{subscription_id}")
    if row is None:
        db.add(Setting(key=f"{LAST_KEY_PREFIX}{subscription_id}", value=value))
    else:
        row.value = value


def _normalize(value: str) -> str:
    return _NORMALIZER.sub("", str(value or "").casefold())


def _title_matches(media_title: str, candidate_title: str) -> bool:
    left, right = _normalize(media_title), _normalize(candidate_title)
    if len(left) < 2 or not right:
        return False
    if left in right or right in left:
        return True
    return SequenceMatcher(None, left, right).ratio() >= 0.72


def _year_matches(media_year: int | None, title: str) -> bool:
    if not media_year:
        return True
    found = [int(match.group(0)) for match in _YEAR.finditer(str(title or ""))]
    if not found:
        return True
    return any(abs(year - int(media_year)) <= 1 for year in found)


def _quality_bucket(text: str) -> str:
    match = _RESOLUTION.search(text or "")
    if match is None:
        return "sd"
    value = match.group(1).lower()
    if value in {"4k", "2160p"}:
        return "4k"
    if value == "1080p":
        return "1080p"
    if value == "720p":
        return "720p"
    return "sd"


def _bucket_ok(bucket: str, min_bucket: str) -> bool:
    if min_bucket not in BUCKET_ORDER:
        return True
    if bucket not in BUCKET_ORDER:
        return False
    return BUCKET_ORDER.index(bucket) >= BUCKET_ORDER.index(min_bucket)


def _episode_owned(db: Session, media_id: int, season: int, episode: int) -> bool:
    return (
        db.scalar(
            select(LibraryFile.id)
            .join(Episode, LibraryFile.episode_id == Episode.id)
            .join(Season, Episode.season_id == Season.id)
            .where(
                Season.media_id == media_id,
                Season.season_number == season,
                Episode.episode_number == episode,
            )
            .limit(1)
        )
        is not None
    )


def _min_bucket(subscription: Subscription) -> str:
    try:
        pref = json.loads(subscription.quality_pref or "{}")
    except (TypeError, json.JSONDecodeError):
        pref = {}
    value = str((pref or {}).get("min_bucket") or "1080p").lower()
    return value if value in BUCKET_ORDER else "1080p"


def search_subscription(
    db: Session,
    subscription: Subscription,
    *,
    limit: int = 20,
    auto_transfer: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """为单部订阅搜一轮，命中缺失集时落候选并按需自动建任务。"""
    media = db.get(MediaItem, subscription.media_id)
    if media is None:
        return {"ok": False, "message": "订阅媒体不存在", "candidates": 0, "tasks": []}
    is_movie = str(media.type or "").lower() == "movie"
    season_number = 1
    scope = SubscriptionScope.from_json(subscription.scope)
    if getattr(scope, "seasons", None):
        season_number = int(sorted(scope.seasons)[0])
    result = executor.search_resources(
        db,
        keyword=str(media.title or ""),
        media_type="movie" if is_movie else "tv",
        year=media.year,
        season=None if is_movie else season_number,
        limit=limit,
    )
    bucket_min = _min_bucket(subscription)
    created_candidates = 0
    created_tasks: list[int] = []
    skipped: dict[str, int] = {}
    repository = SqlAlchemyTaskRepository(db)

    for item in result["items"]:
        provider = str(item.get("resource_type") or "").lower()
        if provider not in _TRANSFERABLE_PROVIDERS or not item.get("can_transfer"):
            skipped["non_share"] = skipped.get("non_share", 0) + 1
            continue
        title = str(item.get("title") or "")
        if not _title_matches(str(media.title or ""), title):
            skipped["title"] = skipped.get("title", 0) + 1
            continue
        if not _year_matches(media.year, title):
            skipped["year"] = skipped.get("year", 0) + 1
            continue
        bucket = _quality_bucket(title)
        if not _bucket_ok(bucket, bucket_min):
            skipped["quality"] = skipped.get("quality", 0) + 1
            continue
        parsed_season, parsed_episode = parse_episode_from_name(title)
        season = parsed_season or season_number
        whole_season = False
        if is_movie:
            season, episode = 1, 1
            if _episode_owned(db, media.id, season, episode):
                skipped["owned"] = skipped.get("owned", 0) + 1
                continue
        elif parsed_episode is None:
            whole_season = True
            episode = 0
        else:
            episode = int(parsed_episode)
            if not scope.accepts(EpisodeKey(season, episode)):
                skipped["scope"] = skipped.get("scope", 0) + 1
                continue
            if _episode_owned(db, media.id, season, episode):
                skipped["owned"] = skipped.get("owned", 0) + 1
                continue

        url = str(item.get("url") or "")
        dedup = dedup_key(provider, url)
        if db.scalar(select(DiscoveredResource.id).where(DiscoveredResource.dedup_key == dedup)):
            skipped["duplicate"] = skipped.get("duplicate", 0) + 1
            continue
        if dry_run:
            created_candidates += 1
            continue

        key = idempotency_key(provider, url, season, episode or 1, bucket)
        resource = DiscoveredResource(
            subscription_id=subscription.id,
            provider=provider,
            share_url=url,
            dedup_key=dedup,
            idempotency_key=None if whole_season else key,
            score=score(bucket, has_subtitles=True),
            state="discovered",
            payload=json.dumps(
                {
                    "source": item.get("source") or "",
                    "source_name": item.get("source_name") or "",
                    "title": title,
                    "season": season,
                    "episode": episode,
                    "quality_bucket": bucket,
                    "password": item.get("password") or "",
                    "size_text": item.get("size_text") or "",
                    "update_time": item.get("update_time") or "",
                    "whole_season": whole_season,
                    "auto_search": True,
                },
                ensure_ascii=False,
            ),
        )
        db.add(resource)
        db.flush()
        created_candidates += 1

        if auto_transfer and not whole_season and len(created_tasks) < 3:
            task_id, created = repository.create_or_get(
                key, subscription_id=subscription.id, resource_id=resource.id
            )
            resource.state = "accepted"
            if created:
                created_tasks.append(task_id)
    db.commit()
    _mark_run(db, subscription.id)
    db.commit()
    return {
        "ok": True,
        "subscription_id": subscription.id,
        "title": media.title,
        "candidates": created_candidates,
        "tasks": created_tasks,
        "skipped": skipped,
        "sources_ok": [s["id"] for s in result["sources"] if s["status"] == "ok"],
        "elapsed_ms": result["elapsed_ms"],
    }


def due_subscriptions(db: Session, interval_hours: int) -> list[Subscription]:
    rows = db.scalars(
        select(Subscription).where(Subscription.state == "active").order_by(Subscription.id)
    ).all()
    cutoff = datetime.now(UTC) - timedelta(hours=interval_hours)
    due = []
    for subscription in rows:
        last = _last_run(db, subscription.id)
        if last is None or last.tzinfo is None or last <= cutoff:
            due.append(subscription)
    return due


def run_round(db: Session, *, force: bool = False) -> dict[str, Any]:
    """跑一轮订阅搜源；``force=True`` 忽略间隔与总开关（手动触发用）。"""
    config = load_settings(db)
    if not config["enabled"] and not force:
        return {"ok": True, "skipped": "auto_search_disabled", "processed": []}
    subscriptions = (
        db.scalars(
            select(Subscription).where(Subscription.state == "active").order_by(Subscription.id)
        ).all()
        if force
        else due_subscriptions(db, int(config["interval_hours"]))
    )
    limit = int(config["max_per_round"])
    processed: list[dict[str, Any]] = []
    for subscription in subscriptions[:limit]:
        try:
            processed.append(
                search_subscription(
                    db,
                    subscription,
                    limit=int(config["per_subscription_limit"]),
                    auto_transfer=bool(config["auto_transfer"]),
                )
            )
        except Exception as error:  # 单部订阅失败不影响其它
            db.rollback()
            logger.info(f"[auto_search] subscription={subscription.id} 失败：{error}")
            processed.append(
                {
                    "ok": False,
                    "subscription_id": subscription.id,
                    "message": str(error)[:200],
                }
            )
    return {
        "ok": True,
        "interval_hours": int(config["interval_hours"]),
        "auto_transfer": bool(config["auto_transfer"]),
        "total": len(processed),
        "candidates": sum(int(row.get("candidates") or 0) for row in processed),
        "tasks": sum(len(row.get("tasks") or []) for row in processed),
        "processed": processed,
    }
