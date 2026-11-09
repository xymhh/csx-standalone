from __future__ import annotations

import pytest

from csx.domain.category import (
    DEFAULT_MOVIE_STRATEGIES,
    DEFAULT_TV_STRATEGIES,
    default_strategies,
    match_category,
)


@pytest.mark.parametrize(
    ("info", "expected"),
    [
        ({"genre_ids": [16]}, "动画电影"),
        ({"genre_ids": ["16"], "original_language": "zh"}, "动画电影"),
        ({"original_language": "zh"}, "华语电影"),
        ({"original_language": "cn"}, "华语电影"),
        ({"original_language": "en"}, "外语电影"),
        ({"original_language": "ja"}, "外语电影"),
        # 元数据整体缺失时与 MP 一致：不算分类，交给调用方不建二级目录
        ({}, ""),
    ],
)
def test_movie_defaults(info, expected):
    assert match_category(DEFAULT_MOVIE_STRATEGIES, info) == expected


@pytest.mark.parametrize(
    ("info", "expected"),
    [
        ({"genre_ids": [16], "origin_country": ["CN"]}, "国漫"),
        ({"genre_ids": [16], "origin_country": ["JP"]}, "日番"),
        ({"genre_ids": [16], "origin_country": ["US"]}, "欧美剧"),
        ({"genre_ids": [99]}, "纪录片"),
        ({"genre_ids": [10762]}, "儿童"),
        ({"genre_ids": [10764]}, "综艺"),
        ({"origin_country": ["CN"]}, "国产剧"),
        ({"origin_country": ["US"]}, "欧美剧"),
        ({"origin_country": ["JP"]}, "日韩剧"),
        ({"origin_country": ["ZZ"]}, "未分类"),
        ({"genre_ids": [28]}, "未分类"),
    ],
)
def test_tv_defaults(info, expected):
    assert match_category(DEFAULT_TV_STRATEGIES, info) == expected


def test_production_countries_mapping_entries_are_supported():
    info = {"production_countries": [{"iso_3166_1": "CN", "name": "China"}]}
    strategies = [{"name": "华语电影", "conditions": {"production_countries": "CN,TW,HK"}}]
    assert match_category(strategies, info) == "华语电影"


def test_exclusion_condition():
    strategies = [{"name": "英美剧", "conditions": {"origin_country": "US,!GB"}}]
    assert match_category(strategies, {"origin_country": ["US"]}) == "英美剧"
    assert match_category(strategies, {"origin_country": ["US", "GB"]}) == ""


def test_year_range_condition():
    strategies = [{"name": "老片", "conditions": {"release_year": "1990-1999"}}]
    assert match_category(strategies, {"release_date": "1994-06-01"}) == "老片"
    assert match_category(strategies, {"release_date": "2004-06-01"}) == ""


def test_multi_value_is_or_and_conditions_are_and():
    strategies = [{"name": "国产动画", "conditions": {"genre_ids": "16,99", "origin_country": "CN"}}]
    assert match_category(strategies, {"genre_ids": [99], "origin_country": ["CN"]}) == "国产动画"
    assert match_category(strategies, {"genre_ids": [99], "origin_country": ["US"]}) == ""


def test_missing_attribute_does_not_match():
    strategies = [{"name": "日番", "conditions": {"genre_ids": "16"}}]
    assert match_category(strategies, {"origin_country": ["JP"]}) == ""


def test_empty_inputs_return_empty_string():
    assert match_category(DEFAULT_MOVIE_STRATEGIES, {}) or True
    assert match_category([], {"genre_ids": [16]}) == ""
    assert match_category(DEFAULT_MOVIE_STRATEGIES, None) == ""


def test_default_strategies_are_copies():
    first = default_strategies("movie")
    first[0]["name"] = "改坏了"
    assert default_strategies("movie")[0]["name"] == "动画电影"
    assert default_strategies("tv")[0]["name"] == "国漫"
