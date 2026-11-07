"""Telegram message matching and persistence orchestration."""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.adapters.db.repositories import SqlAlchemyTaskRepository
from csx.domain.media import EpisodeKey
from csx.domain.resource import dedup_key, idempotency_key, score
from csx.domain.subscription import SubscriptionScope
from csx.domain.tg import extract_telegram_links, extract_telegram_title
from csx.infra.models import (
    DiscoveredResource,
    Episode,
    LibraryFile,
    MediaItem,
    Season,
    Subscription,
)

_TITLE_NORMALIZER = re.compile(r"[^\w\u3400-\u9fff]+", re.UNICODE)
_RESOLUTION = re.compile(r"(?i)(2160p|4k|1080p|720p|480p)")


def _normalize_title(value: str) -> str:
    return _TITLE_NORMALIZER.sub("", value.casefold())


def match_active_subscription(session: Session, title: str) -> Subscription | None:
    """Find the strongest active title match using containment or fuzzy ratio."""
    normalized = _normalize_title(title)
    if len(normalized) < 2:
        return None
    candidates = session.execute(
        select(Subscription, MediaItem)
        .join(MediaItem, Subscription.media_id == MediaItem.id)
        .where(Subscription.state == "active")
        .order_by(Subscription.id)
    ).all()
    best: tuple[float, Subscription] | None = None
    for subscription, media in candidates:
        media_title = _normalize_title(media.title)
        ratio = SequenceMatcher(None, normalized, media_title).ratio()
        if normalized in media_title or media_title in normalized:
            ratio = max(ratio, 0.88)
        if ratio >= 0.68 and (best is None or ratio > best[0]):
            best = ratio, subscription
    return best[1] if best else None


def parse_telegram_message(
    session: Session,
    text: str,
    extra_urls: list[str] | None = None,
) -> dict[str, Any]:
    title, season, episode = extract_telegram_title(text)
    subscription = match_active_subscription(session, title) if title else None
    return {
        "title": title,
        "season": season,
        "episode": episode,
        "links": extract_telegram_links(text, extra_urls or []),
        "matched_subscription_id": subscription.id if subscription else None,
    }


def _quality_from_text(text: str) -> str:
    match = _RESOLUTION.search(text or "")
    if match is None:
        return "sd"
    resolution = match.group(1).lower()
    return (
        "4k"
        if resolution in {"4k", "2160p"}
        else "1080p"
        if resolution == "1080p"
        else "720p"
        if resolution == "720p"
        else "sd"
    )


def _episode_is_owned(session: Session, media_id: int, season: int, episode: int) -> bool:
    return (
        session.scalar(
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


def ingest_telegram_message(
    session: Session,
    *,
    channel: str,
    message_id: int | None,
    text: str,
    auto_transfer: bool = True,
) -> dict[str, Any]:
    """Parse a Telegram post, persist matching missing candidates and queued tasks."""
    parsed = parse_telegram_message(session, text)
    subscription_id = parsed["matched_subscription_id"]
    subscription = session.get(Subscription, subscription_id) if subscription_id else None
    season = int(parsed["season"] or 1)
    episode = parsed["episode"]
    if subscription is None or episode is None:
        return {
            "ingested": False,
            "resources_count": 0,
            "tasks_created": [],
            "message": "未识别到可匹配的缺失剧集订阅或集数",
        }

    media = session.get(MediaItem, subscription.media_id)
    if media is None:
        return {
            "ingested": False,
            "resources_count": 0,
            "tasks_created": [],
            "message": "订阅媒体不存在",
        }
    scope = SubscriptionScope.from_json(subscription.scope)
    if not scope.accepts(EpisodeKey(season, int(episode))):
        return {
            "ingested": False,
            "resources_count": 0,
            "tasks_created": [],
            "message": "该集不在订阅范围内",
        }
    if _episode_is_owned(session, media.id, season, int(episode)):
        return {
            "ingested": False,
            "resources_count": 0,
            "tasks_created": [],
            "message": "该集已在媒体库中",
        }

    links = parsed["links"]
    if not links:
        return {
            "ingested": False,
            "resources_count": 0,
            "tasks_created": [],
            "message": "消息中没有识别到网盘分享链接",
        }

    bucket = _quality_from_text(text)
    tasks_created: list[int] = []
    created_resources = 0
    task_repository = SqlAlchemyTaskRepository(session)
    for link in links:
        provider = str(link["provider"])
        url = str(link["url"])
        dedup = dedup_key(provider, url)
        resource = session.scalar(
            select(DiscoveredResource).where(DiscoveredResource.dedup_key == dedup)
        )
        resource_key = idempotency_key(provider, url, season, int(episode), bucket)
        if resource is None:
            resource = DiscoveredResource(
                subscription_id=subscription.id,
                provider=provider,
                share_url=url,
                dedup_key=dedup,
                idempotency_key=resource_key,
                score=score(bucket, has_subtitles=True),
                state="discovered",
                payload=json.dumps(
                    {
                        "source": "telegram",
                        "channel": channel,
                        "message_id": message_id,
                        "title": parsed["title"],
                        "season": season,
                        "episode": int(episode),
                        "quality_bucket": bucket,
                        "password": link["password"],
                    },
                    ensure_ascii=False,
                ),
            )
            session.add(resource)
            session.flush()
            created_resources += 1

        if auto_transfer:
            task_id, created = task_repository.create_or_get(
                resource_key,
                subscription_id=subscription.id,
                resource_id=resource.id,
            )
            if created:
                tasks_created.append(task_id)

    return {
        "ingested": bool(created_resources or tasks_created),
        "resources_count": created_resources,
        "tasks_created": tasks_created,
        "message": "已创建频道候选资源"
        if created_resources
        else "资源已存在，已按幂等键检查转存任务",
    }
