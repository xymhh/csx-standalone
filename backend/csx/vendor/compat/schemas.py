"""Schema names referenced by vendored search and media utilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MediaType(StrEnum):
    TV = "tv"
    MOVIE = "movie"


class MediaSource(StrEnum):
    THEMOVIEDB = "themoviedb"
    DOUBAN = "douban"
    BANGUMI = "bangumi"
    ANILIST = "anilist"
    IMDB = "imdb"
    TVDB = "tvdb"


@dataclass
class MediaInfo:
    title: str = ""
    year: int | None = None
    tmdb_id: int | None = None
