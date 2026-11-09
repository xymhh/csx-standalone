from __future__ import annotations

from csx.vendor.utils.cache import create_platform_ttl_cache


def _cache(name: str):
    return create_platform_ttl_cache(name, maxsize=10, ttl=60)


def test_setitem_roundtrip_keeps_list_of_dict():
    """__setitem__ 曾把值编码两次，读回来是 {'__csx__': 'list', ...} 而不是列表。"""
    cache = _cache("test:setitem")
    rows = [{"id": "1", "name": "01.mkv", "is_dir": False}]
    cache["k"] = rows
    cached = cache["k"]
    assert isinstance(cached, list)
    assert isinstance(cached[0], dict)
    assert cached == rows


def test_set_roundtrip_keeps_list_of_dict():
    cache = _cache("test:set")
    rows = [{"id": "2", "name": "10.mkv", "is_dir": False}]
    cache.set("k", rows)
    assert cache.get("k") == rows


def test_setitem_and_set_are_equivalent():
    cache = _cache("test:equiv")
    rows = [{"n": "a"}]
    cache["a"] = rows
    cache.set("b", rows)
    assert cache["a"] == cache.get("b") == rows
