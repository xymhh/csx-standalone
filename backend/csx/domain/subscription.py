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
        if self.latest_count <= 0:
            return True
        # 按 episode number 降序排序
        sorted_aired = sorted(aired_episodes_for_season, key=lambda e: e.key.episode, reverse=True)
        latest_eps = sorted_aired[: self.latest_count]
        latest_ep_numbers = {e.key.episode for e in latest_eps}
        return episode.key.episode in latest_ep_numbers


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

    all_aired = aired_episodes(seasons, check_today)

    result: list[EpisodeKey] = []
    for key in all_aired:
        # 找到对应的剧集对象（用于 LATEST 模式的判断）
        episode_obj: Episode | None = None
        for season in seasons:
            if season.number == key.season:
                for ep in season.episodes:
                    if ep.key == key:
                        episode_obj = ep
                        break
                if episode_obj:
                    break

        if episode_obj is None:
            continue

        # 季过滤 + mode 过滤
        if not scope.accepts(key):
            continue

        # LATEST 模式特殊处理
        if scope.mode == ScopeMode.LATEST and episode_obj is not None:
            aired_for_season = scope._aired_in_season(
                next((s for s in seasons if s.number == key.season), None), check_today
            )
            if not scope._should_include_latest(episode_obj, aired_for_season):
                continue

        if key not in owned_set:
            result.append(key)

    # 已排序且去重（all_aired 已经排过，但为了安全再去一次）
    seen: set[tuple[int, int]] = set()
    unique: list[EpisodeKey] = []
    for k in result:
        kt = (k.season, k.episode)
        if kt not in seen:
            seen.add(kt)
            unique.append(k)
    return unique


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

    for season in seasons:
        # 该季所有剧集
        all_eps = season.episodes
        if not all_eps:
            progress[season.number] = (0, 0)
            continue

        # 该季已播出集
        aired = scope._aired_in_season(season, check_today)

        # 该季已播出且被 scope 接受的集
        filtered: list[Episode] = []
        for ep in aired:
            key = ep.key
            if scope.mode == ScopeMode.LATEST and not scope._should_include_latest(ep, aired):
                continue
            if scope.accepts(key):
                filtered.append(ep)

        should = len(filtered)
        has = sum(1 for ep in filtered if ep.key in owned_set)

        progress[season.number] = (has, should)

    return progress
