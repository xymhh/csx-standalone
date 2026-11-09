"""媒体二级分类策略，语义与 MoviePilot 的 `category.yaml` 保持一致。

规则：
1. 按配置顺序匹配，第一个命中的胜出；条件为空表示兜底。
2. 同一规则内多个条件为 AND。
3. 单个条件的值用 `,` 分隔，多值为 OR；`!值` 表示排除；`YYYY-YYYY` 表示区间。
4. 电影看 `production_countries`，剧集看 `origin_country`；年份取上映日期前四位。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

DEFAULT_MOVIE_STRATEGIES: list[dict[str, Any]] = [
    {"name": "动画电影", "conditions": {"genre_ids": "16"}},
    {"name": "华语电影", "conditions": {"original_language": "zh,cn,bo,za"}},
    {"name": "外语电影", "conditions": {}},
]

DEFAULT_TV_STRATEGIES: list[dict[str, Any]] = [
    {"name": "国漫", "conditions": {"genre_ids": "16", "origin_country": "CN,TW,HK"}},
    {"name": "日番", "conditions": {"genre_ids": "16", "origin_country": "JP"}},
    {"name": "纪录片", "conditions": {"genre_ids": "99"}},
    {"name": "儿童", "conditions": {"genre_ids": "10762"}},
    {"name": "综艺", "conditions": {"genre_ids": "10764,10767"}},
    {"name": "国产剧", "conditions": {"origin_country": "CN,TW,HK"}},
    {
        "name": "欧美剧",
        "conditions": {"origin_country": "US,FR,GB,DE,ES,IT,NL,PT,RU,UK"},
    },
    {"name": "日韩剧", "conditions": {"origin_country": "JP,KP,KR,TH,IN,SG"}},
    {"name": "未分类", "conditions": {}},
]

_COUNTRY_KEYS = {"production_countries", "origin_country"}


def default_strategies(media_type: str) -> list[dict[str, Any]]:
    """返回某媒体类型的默认策略副本（避免调用方改到常量）。"""
    source = (
        DEFAULT_TV_STRATEGIES
        if str(media_type or "").lower() in {"tv", "剧集", "电视剧"}
        else DEFAULT_MOVIE_STRATEGIES
    )
    return [
        {"name": item["name"], "conditions": dict(item.get("conditions") or {})} for item in source
    ]


def _info_values(info: Mapping[str, Any], attr: str) -> list[str]:
    if attr == "release_year":
        raw = info.get("release_date") or info.get("first_air_date")
        if not raw:
            return []
        return [str(raw)[:4]]
    raw = info.get(attr)
    if not raw:
        return []
    if attr in _COUNTRY_KEYS:
        values = []
        for entry in raw if isinstance(raw, (list, tuple)) else [raw]:
            if isinstance(entry, Mapping):
                code = entry.get("iso_3166_1")
                if code:
                    values.append(str(code).upper())
            elif entry:
                values.append(str(entry).upper())
        return values
    if isinstance(raw, (list, tuple, set)):
        return [str(entry).upper() for entry in raw]
    return [str(raw).upper()]


def _expand(values: Any) -> list[str]:
    expanded: list[str] = []
    for token in str(values or "").split(","):
        token = token.strip()
        if not token:
            continue
        prefix = "!" if token.startswith("!") else ""
        body = token[1:] if prefix else token
        if "-" in body:
            begin, _, end = body.partition("-")
            if begin.isdigit() and end.isdigit():
                expanded.extend(f"{prefix}{value}" for value in range(int(begin), int(end) + 1))
                continue
            expanded.extend([f"{prefix}{begin}", f"{prefix}{end}"])
            continue
        expanded.append(token)
    return expanded


def _matches(conditions: Mapping[str, Any], info: Mapping[str, Any]) -> bool:
    for attr, value in (conditions or {}).items():
        if value in (None, ""):
            continue
        actual = _info_values(info, attr)
        if not actual:
            return False
        expanded = [entry.upper() for entry in _expand(value)]
        required = [entry for entry in expanded if not entry.startswith("!")]
        excluded = [entry[1:] for entry in expanded if entry.startswith("!")]
        if required and not set(required) & set(actual):
            return False
        if excluded and set(excluded) & set(actual):
            return False
    return True


def match_category(strategies: Sequence[Mapping[str, Any]], info: Mapping[str, Any]) -> str:
    """按顺序返回第一个命中的分类名；全不命中返回空串。"""
    if not info or not strategies:
        return ""
    for item in strategies:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        if _matches(item.get("conditions") or {}, info):
            return name
    return ""
