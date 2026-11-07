"""订阅域模型：范围、接受逻辑、已播集计算。"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from csx.domain.media import Episode, EpisodeKey, Season


class ScopeMode(StrEnum):
    """订阅范围模式。"""

    ALL = "all"
    RANGE = "range"
    LATEST = "latest"


@dataclass(frozen=True)
class SubscriptionScope:
    """订阅范围定义。"""

    mode: ScopeMode = ScopeMode.ALL
    seasons: tuple[int, ...] = ()
    from_episode: int | None = None
    to_episode: int | None = None
    latest_count: int = 0

    @classmethod
    def from_json(cls, raw: str | dict | None) -> SubscriptionScope:
        """从 JSON 解析，非法输入回退默认值（不抛异常）。"""
        if raw is None or raw == "":
            return cls()
        try:
            data = raw if isinstance(raw, dict) else json.loads(raw)
            if not isinstance(data, dict):
                return cls()
        except (json.JSONDecodeError, TypeError):
            return cls()

        mode_str = data.get("mode")
        if mode_str not in (ScopeMode.ALL, ScopeMode.RANGE, ScopeMode.LATEST):
            mode = ScopeMode.ALL
        else:
            mode = mode_str

        # seasons: 去重、升序、丢弃负数
        raw_seasons = data.get("seasons", ())
        if not isinstance(raw_seasons, (list, tuple)):
            raw_seasons = ()
        seasons_set: set[int] = set()
        for s in raw_seasons:
            if isinstance(s, int) and s >= 0:
                seasons_set.add(s)
        seasons = tuple(sorted(seasons_set))

        # from_episode / to_episode: 必须是非负整数或 None
        from_ep = data.get("from_episode")
        if not (from_ep is None or (isinstance(from_ep, int) and from_ep >= 0)):
            from_ep = None

        to_ep = data.get("to_episode")
        if not (to_ep is None or (isinstance(to_ep, int) and to_ep >= 0)):
            to_ep = None

        # latest_count: 非负整数，否则 0
        lc = data.get("latest_count", 0)
        if not (isinstance(lc, int) and lc >= 0):
            lc = 0

        return cls(
            mode=mode,
            seasons=seasons,
            from_episode=from_ep,
            to_episode=to_ep,
            latest_count=lc,
        )

    def to_json(self) -> str:
        """序列化为紧凑 JSON，字段顺序固定，ensure_ascii=False。"""
        data = {
            "mode": self.mode,
            "seasons": self.seasons,
            "from_episode": self.from_episode,
            "to_episode": self.to_episode,
            "latest_count": self.latest_count,
        }
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    def accepts(self, key: EpisodeKey) -> bool:
        """判断是否接受该集。"""
        # 季过滤（seasons 非空则必须命中）
        if self.seasons and key.season not in self.seasons:
            return False

        if self.mode == ScopeMode.ALL:
            return True

        if self.mode == ScopeMode.RANGE:
            from_ep = self.from_episode
            to_ep = self.to_episode
            if from_ep is not None and key.episode < from_ep:
                return False
            return to_ep is None or key.episode <= to_ep

        return self.mode == ScopeMode.LATEST

    def _is_aired(self, episode: Episode, today: date | None) -> bool:
        """判断一集是否已播出。"""
        if episode.air_date is None:
            return True
        check_today = today or date.today()
        return episode.air_date <= check_today

    def _aired_in_season(self, season: Season, today: date | None) -> list[Episode]:
        """返回某季中已播出的剧集列表。"""
        aired_list: list[Episode] = []
        for ep in season.episodes:
            if self._is_aired(ep, today):
                aired_list.append(ep)
        return aired_list

    def _should_include_latest(
        self,
        episode: Episode,
        aired_episodes_for_season: list[Episode],
    ) -> bool:
        """在 LATEST 模式下，判断是否应包含该集。"""
        latest_numbers = self._latest_numbers(aired_episodes_for_season)
        if latest_numbers is None:
            return True
        return episode.key.episode in latest_numbers

    def _latest_numbers(self, aired_in_season: list[Episode]) -> set[int] | None:
        """LATEST 模式下该季被接受的集号集合；非 LATEST 或 latest_count<=0 返回 None（不设限）。"""
        if self.mode is not ScopeMode.LATEST or self.latest_count <= 0:
            return None
        ordered = sorted(aired_in_season, key=lambda e: e.key.episode, reverse=True)
        return {episode.key.episode for episode in ordered[: self.latest_count]}


def aired_episodes(
    seasons: Iterable[Season],
    today: date | None = None,
) -> list[EpisodeKey]:
    """返回所有已播出的集（air_date 为 None 视为已播，未来不算）。"""
    result: list[EpisodeKey] = []
    check_today = today or date.today()

    for season in seasons:
        for episode in season.episodes:
            if episode.air_date is None or episode.air_date <= check_today:
                result.append(episode.key)

    # 按 (season, episode) 升序排序并去重
    result.sort(key=lambda k: (k.season, k.episode))
    seen: set[tuple[int, int]] = set()
    unique: list[EpisodeKey] = []
    for k in result:
        key_tuple = (k.season, k.episode)
        if key_tuple not in seen:
            seen.add(key_tuple)
            unique.append(k)
    return unique


def missing_episodes(
    seasons: Iterable[Season],
    owned: Iterable[EpisodeKey],
    scope: SubscriptionScope,
    today: date | None = None,
) -> list[EpisodeKey]:
    """返回已播 ∧ scope.accepts ∧ 不在 owned 的集（升序、去重）。"""
    owned_set: set[EpisodeKey] = set(owned)
    check_today = today or date.today()
    season_list = tuple(seasons)

    result: set[EpisodeKey] = set()
    for season in season_list:
        aired = scope._aired_in_season(season, check_today)
        latest_numbers = scope._latest_numbers(aired)
        for episode in aired:
            key = episode.key
            if not scope.accepts(key):
                continue
            if latest_numbers is not None and key.episode not in latest_numbers:
                continue
            if key in owned_set:
                continue
            result.add(key)

    return sorted(result)


def season_progress(
    seasons: Iterable[Season],
    owned: Iterable[EpisodeKey],
    scope: SubscriptionScope,
    today: date | None = None,
) -> dict[int, tuple[int, int]]:
    """返回每季进度：{季号：(已入库，应入库)}。"""
    owned_set: set[EpisodeKey] = set(owned)
    check_today = today or date.today()

    progress: dict[int, tuple[int, int]] = {}

    for season in tuple(seasons):
        aired = scope._aired_in_season(season, check_today)
        latest_numbers = scope._latest_numbers(aired)

        accepted = [
            episode
            for episode in aired
            if scope.accepts(episode.key)
            and (latest_numbers is None or episode.key.episode in latest_numbers)
        ]
        has = sum(1 for episode in accepted if episode.key in owned_set)
        progress[season.number] = (has, len(accepted))

    return progress
