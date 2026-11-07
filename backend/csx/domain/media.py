"""媒体领域模型：类型、剧集键、剧集、季、媒体项。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class MediaType(StrEnum):
    """媒体类型。"""

    TV = "tv"
    MOVIE = "movie"


@dataclass(frozen=True, order=True)
class EpisodeKey:
    """剧集键（用于唯一标识一集）。"""

    season: int
    episode: int

    def __str__(self) -> str:
        """返回 S01E02 格式的字符串（季和集都两位补零）。"""
        return f"S{self.season:02d}E{self.episode:02d}"


@dataclass(frozen=True)
class Episode:
    """剧集信息。"""

    key: EpisodeKey
    air_date: date | None = None
    title: str = ""


@dataclass(frozen=True)
class Season:
    """季信息。"""

    number: int
    episodes: tuple[Episode, ...] = ()


@dataclass(frozen=True)
class MediaItem:
    """媒体项（剧或电影）。"""

    tmdb_id: int
    type: MediaType
    title: str
    year: int | None = None
    seasons: tuple[Season, ...] = ()
