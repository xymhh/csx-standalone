"""本地 UI 预览用种子数据（不进入生产）。"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import os

from csx.infra.db import (
    SessionLocal,
    engine,
)
from csx.infra.migrations import upgrade_to_head
from csx.infra.models import (
    DiscoveredResource,
    Episode,
    LibraryFile,
    MediaItem,
    Season,
    Subscription,
    TransferTask,
)

data_dir = os.environ.get("CSX_DATA_DIR", "")
if "tmp" not in data_dir and "preview" not in data_dir:
    raise SystemExit("拒绝执行：请把 CSX_DATA_DIR 指向临时目录，避免污染真实数据")

upgrade_to_head(engine)

POSTERS = {
    "谷雨": "https://image.tmdb.org/t/p/w200/8b8R8l88Qje9dn9OE8PY05Nxl1X.jpg",
    "奥德赛": "https://image.tmdb.org/t/p/w200/1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg",
}

now = datetime.now(UTC).replace(tzinfo=None)


def media(title: str, year: int, type_: str) -> int:
    with SessionLocal() as db:
        row = MediaItem(
            tmdb_id=abs(hash(title)) % 1_000_000,
            type=type_,
            title=title,
            year=year,
            poster_url=POSTERS.get(title, ""),
        )
        db.add(row)
        db.commit()
        return row.id


def add_episode(media_id: int, season_number: int, episode_number: int) -> int:
    with SessionLocal() as db:
        season = (
            db.query(Season)
            .filter_by(media_id=media_id, season_number=season_number)
            .one_or_none()
        )
        if season is None:
            season = Season(media_id=media_id, season_number=season_number)
            db.add(season)
            db.flush()
        episode = Episode(season_id=season.id, episode_number=episode_number)
        db.add(episode)
        db.commit()
        return episode.id


def add_file(
    media_id: int, season_number: int, episode_number: int, path: str, size: int
):
    episode_id = add_episode(media_id, season_number, episode_number)
    with SessionLocal() as db:
        db.add(
            LibraryFile(
                episode_id=episode_id,
                path=path,
                size=size,
                quality_bucket="2160p",
                provider="115",
            )
        )
        db.commit()


def task(
    media_id: int,
    *,
    provider: str,
    title: str,
    season: int | None,
    episode: int | None,
    state: str,
    stage: str = "",
    attempt: int = 1,
    error: str = "",
    age_minutes: int = 5,
):
    with SessionLocal() as db:
        sub = Subscription(
            media_id=media_id, scope="{}", quality_pref="{}", source="manual"
        )
        db.add(sub)
        db.flush()
        resource = DiscoveredResource(
            subscription_id=sub.id,
            provider=provider,
            share_url=f"https://pan.quark.cn/s/{abs(hash(title + state)) % 10**10}",
            dedup_key=f"{title}-{state}-{age_minutes}",
            payload=json.dumps(
                {
                    "title": title,
                    "season": season,
                    "episode": episode,
                    "quality_bucket": "2160p",
                },
                ensure_ascii=False,
            ),
        )
        db.add(resource)
        db.flush()
        when = now - timedelta(minutes=age_minutes)
        db.add(
            TransferTask(
                idempotency_key=f"{title}-{state}-{age_minutes}",
                subscription_id=sub.id,
                resource_id=resource.id,
                state=state,
                stage=stage,
                attempt=attempt,
                last_error=error,
                next_retry_at=(now + timedelta(seconds=45))
                if state == "retry_wait"
                else None,
                created_at=when,
                updated_at=when + timedelta(minutes=1),
            )
        )
        db.commit()


gu = media("谷雨", 2026, "tv")
odyssey = media("奥德赛", 2026, "movie")
season = media("漫长的季节", 2023, "tv")

task(
    gu,
    provider="quark",
    title="谷雨 (2026) S01E12 2160p WEB-DL H265",
    season=1,
    episode=12,
    state="running",
    stage="organizing",
    attempt=1,
    age_minutes=3,
)
task(
    gu,
    provider="115",
    title="谷雨 (2026) S01E13 2160p WEB-DL H265",
    season=1,
    episode=13,
    state="queued",
    age_minutes=1,
)
task(
    odyssey,
    provider="115",
    title="奥德赛 (2026) 2160p UHD BluRay REMUX",
    season=1,
    episode=1,
    state="retry_wait",
    attempt=2,
    error="分享失效",
    age_minutes=8,
)
task(
    season,
    provider="quark",
    title="漫长的季节 (2023) S01E05 1080p WEB-DL",
    season=1,
    episode=5,
    state="dead_letter",
    attempt=3,
    error="RapidUploadError: 未命中秒传 @ File /app/csx/vendor/core/transfer.py",
    age_minutes=30,
)

for episode in (10, 11):
    add_file(
        gu,
        1,
        episode,
        f"/CSX/媒体库/剧集/谷雨 (2026)/Season 01/谷雨 (2026) - S01E{episode}.mkv",
        3_400_000_000,
    )
    task(
        gu,
        provider="quark",
        title=f"谷雨 (2026) S01E{episode} 2160p WEB-DL H265",
        season=1,
        episode=episode,
        state="succeeded",
        age_minutes=200 + episode,
    )
task(
    gu,
    provider="quark",
    title="谷雨 (2026) S01E09 2160p WEB-DL H265",
    season=1,
    episode=9,
    state="cancelled",
    age_minutes=500,
)

add_file(
    odyssey, 1, 1, "/CSX/媒体库/电影/奥德赛 (2026)/奥德赛 (2026).mkv", 88_000_000_000
)
task(
    odyssey,
    provider="115",
    title="奥德赛 (2026) 2160p UHD BluRay REMUX",
    season=1,
    episode=1,
    state="succeeded",
    age_minutes=1500,
)
task(
    odyssey,
    provider="115",
    title="奥德赛 (2026) 1080p BluRay x264",
    season=1,
    episode=1,
    state="dead_letter",
    attempt=3,
    error="整理失败：目标目录无权限",
    age_minutes=1400,
)

print("seeded")
