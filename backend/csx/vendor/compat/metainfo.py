"""P2 过渡 shim，只做季集粗解析；P3 片名识别正式方案落地后整体替换。"""

from __future__ import annotations

import re


_SEASON_EPISODE = re.compile(r"(?<![A-Za-z0-9])S\s*(\d{1,2})\s*E\s*(\d{1,4})", re.I)
_SEASON_TAG = re.compile(r"(?<![A-Za-z0-9])S\s*(\d{1,2})(?![A-Za-z0-9])", re.I)
_CN_SEASON = re.compile(r"第\s*(\d{1,2})\s*季")
_EPISODE_TAGS = (
    re.compile(r"(?<![A-Za-z0-9])(?:EP|E)\s*(\d{1,4})(?!\d)", re.I),
    re.compile(r"(?<![A-Za-z0-9])P\s*(\d{1,4})(?!\d)", re.I),
    re.compile(r"第\s*(\d{1,4})\s*集"),
)
_EPISODE_COUNT = re.compile(r"共\s*(\d{1,4})\s*集")
_EPISODE_RANGE = re.compile(
    r"(?<![A-Za-z0-9])(?:EP|E|P)\s*(\d{1,4})\s*[-~至]\s*(?:EP|E|P)?\s*(\d{1,4})(?!\d)",
    re.I,
)


class MetaInfo:
    """提供 magnet 元数据提取所需的最低限度季集字段。"""

    def __init__(self, title: str = "") -> None:
        self.begin_season: int | None = None
        self.season_list: list[int] = []
        self.episode_list: list[int] = []
        try:
            self._parse(str(title or ""))
        except Exception:
            self.begin_season = None
            self.season_list = []
            self.episode_list = []

    def _parse(self, title: str) -> None:
        season_episode = _SEASON_EPISODE.search(title)
        if season_episode:
            self.begin_season = int(season_episode.group(1))
            self.season_list = [self.begin_season]
            self.episode_list.append(int(season_episode.group(2)))
        else:
            season = _SEASON_TAG.search(title) or _CN_SEASON.search(title)
            if season:
                self.begin_season = int(season.group(1))
                self.season_list = [self.begin_season]

        for start, end in _EPISODE_RANGE.findall(title):
            first, last = int(start), int(end)
            if last >= first and last - first <= 1000:
                self.episode_list.extend(range(first, last + 1))

        for pattern in _EPISODE_TAGS:
            self.episode_list.extend(int(value) for value in pattern.findall(title))

        count = _EPISODE_COUNT.search(title)
        if count and not self.episode_list:
            self.episode_list.extend(range(1, int(count.group(1)) + 1))

        self.episode_list = sorted(set(self.episode_list))
