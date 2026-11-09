from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from csx.infra.category_config import normalize_strategies, resolve_category_strategies
from csx.infra.models import Base, Setting


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_defaults_when_unconfigured():
    with _session() as db:
        result = resolve_category_strategies(db)
    assert [item["name"] for item in result["movie"]][:2] == ["动画电影", "华语电影"]
    assert result["tv"][0]["name"] == "国漫"


def test_disabled_returns_empty_strategies():
    with _session() as db:
        db.add(Setting(key="category.enabled", value=json.dumps(False)))
        db.commit()
        result = resolve_category_strategies(db)
    assert result == {"movie": [], "tv": []}


def test_custom_strategies_are_used():
    with _session() as db:
        db.add(
            Setting(
                key="category.movie",
                value=json.dumps([{"name": "纪录片", "conditions": {"genre_ids": "99"}}]),
            )
        )
        db.commit()
        result = resolve_category_strategies(db)
    assert result["movie"] == [{"name": "纪录片", "conditions": {"genre_ids": "99"}}]
    assert result["tv"][0]["name"] == "国漫"


def test_normalize_strategies_drops_dirty_entries():
    cleaned = normalize_strategies(
        [
            {"name": "  ", "conditions": {}},
            {"name": "动画电影", "conditions": {"genre_ids": 16, "empty": ""}},
            "not-a-dict",
        ]
    )
    assert cleaned == [{"name": "动画电影", "conditions": {"genre_ids": "16"}}]


def test_normalize_strategies_handles_non_list():
    assert normalize_strategies({"movie": []}) == []
    assert normalize_strategies(None) == []
