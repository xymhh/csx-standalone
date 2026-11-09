from __future__ import annotations

from csx.vendor.utils.memory_cache import InMemoryTTLCache


def test_value_keeps_original_structure():
    cache = InMemoryTTLCache(maxsize=10, ttl=60)
    rows = [{"id": "1", "name": "01.mkv", "is_dir": False}]
    cache["k"] = rows
    cached = cache["k"]
    assert cached == rows
    assert isinstance(cached[0], dict)
    assert cached[0]["name"] == "01.mkv"


def test_missing_key_raises():
    cache = InMemoryTTLCache(maxsize=10, ttl=60)
    assert "k" not in cache
    try:
        cache["k"]
    except KeyError:
        pass
    else:  # pragma: no cover - 防回归
        raise AssertionError("未命中应抛 KeyError")


def test_delete_and_clear():
    cache = InMemoryTTLCache(maxsize=10, ttl=60)
    cache["a"] = 1
    cache["b"] = 2
    cache.delete("a")
    assert "a" not in cache
    assert len(cache) == 1
    cache.clear()
    assert len(cache) == 0
