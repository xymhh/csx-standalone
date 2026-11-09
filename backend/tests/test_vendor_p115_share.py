from __future__ import annotations

from types import SimpleNamespace

import csx.vendor.drive.p115.share as share_module


class _FakeLimiter:
    min_interval = 0.0

    def call(self, func):
        return func()


def _service() -> SimpleNamespace:
    # 用普通对象做 self，避免 OwnerDelegator 的属性代理在未初始化时递归
    return SimpleNamespace(
        client=object(),
        rate_limiter=_FakeLimiter(),
        last_list_error="",
        _share_file_cache={},
        SHARE_PAGE_SIZE=200,
        SHARE_SNAP_PAGE_SIZE=20,
        _should_skip_season_dir=lambda name, season: False,
    )


def _list(service) -> list:
    return share_module.ShareService._list_share_files_recursive(
        service, share_code="abc", receive_code="xyz"
    )


def test_share_iterdir_text_result_is_ignored(monkeypatch):
    """115 风控时 share_iterdir 返回纯文本，不能被 list() 拆成字符条目。"""
    monkeypatch.setattr(
        share_module, "share_iterdir", lambda *args, **kwargs: "请稍后再试", raising=False
    )
    service = _service()
    assert _list(service) == []
    assert "文本" in service.last_list_error


def test_share_iterdir_non_dict_rows_are_skipped(monkeypatch):
    monkeypatch.setattr(
        share_module,
        "share_iterdir",
        lambda *args, **kwargs: [{"id": "1", "name": "01.mkv", "size": 10}, "junk"],
        raising=False,
    )
    files = _list(_service())
    assert [item["name"] for item in files] == ["01.mkv"]
