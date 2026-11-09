from __future__ import annotations

from types import SimpleNamespace

import pytest

from csx.adapters.drive.p115 import P115DriveAdapter


class _FakeMutation:
    def __init__(self, move_ok=True, rename_ok=True):
        self.move_ok = move_ok
        self.rename_ok = rename_ok
        self.calls = []

    def move_file(self, item, target_dir, target_name):
        self.calls.append(("move", item.name, target_dir, target_name))
        return item if self.move_ok else None

    def rename_file(self, path, item, target_name):
        self.calls.append(("rename", path, item.name, target_name))
        return self.rename_ok


def _adapter(mutation=None):
    adapter = P115DriveAdapter(share_service=None, files_service=None, mutation_service=mutation)
    adapter._known["1"] = (SimpleNamespace(id="1", name="01.mkv"), "/CSX/转存")
    return adapter


def test_move_goes_through_mutation_service():
    mutation = _FakeMutation()
    adapter = _adapter(mutation)
    adapter.move("1", "/CSX/媒体库/电影/奥德赛 (2026)")
    assert mutation.calls == [
        ("move", "01.mkv", "/CSX/媒体库/电影/奥德赛 (2026)", "01.mkv"),
    ]
    assert adapter._known["1"][1] == "/CSX/媒体库/电影/奥德赛 (2026)"


def test_move_failure_raises():
    adapter = _adapter(_FakeMutation(move_ok=False))
    with pytest.raises(RuntimeError, match="115 移动文件失败"):
        adapter.move("1", "/CSX/媒体库")


def test_move_without_mutation_capability_raises():
    adapter = _adapter(None)
    with pytest.raises(RuntimeError, match="缺少变更能力"):
        adapter.move("1", "/CSX/媒体库")


def test_move_unregistered_file_raises():
    adapter = _adapter(_FakeMutation())
    with pytest.raises(RuntimeError, match="文件未登记"):
        adapter.move("999", "/CSX/媒体库")


def test_rename_goes_through_mutation_service():
    mutation = _FakeMutation()
    adapter = _adapter(mutation)
    adapter.rename("1", "奥德赛 (2026).mkv")
    assert mutation.calls == [("rename", "/CSX/转存", "01.mkv", "奥德赛 (2026).mkv")]
