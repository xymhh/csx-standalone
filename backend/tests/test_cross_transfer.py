"""跨盘转存：设置解析、库盘选择与中继分支。"""

from __future__ import annotations

from dataclasses import dataclass

from csx.application.transfer import execute_transfer
from csx.domain.task import TaskState
from csx.infra.cross_transfer import _coerce, resolve_cache_dir
from csx.ports.drive import ShareFile, ShareStatus, TransferOutcome


class FakeTasks:
    def __init__(self):
        self.rows = {}
        self.transitions = []

    def create_or_get(self, key, **kwargs):
        created = key not in self.rows
        self.rows.setdefault(key, {"state": TaskState.QUEUED, "attempt": 0})
        return list(self.rows).index(key) + 1, created

    def transition(self, task_id, dst, *, error=""):
        key = list(self.rows)[task_id - 1]
        row = self.rows[key]
        row["state"] = dst
        row["attempt"] += dst is TaskState.RUNNING
        row["error"] = error
        self.transitions.append(dst)

    def get(self, task_id):
        row = list(self.rows.values())[task_id - 1]
        return {"state": row["state"].value, "attempt": row["attempt"]}


class FakeLibrary:
    def __init__(self):
        self.items = {}

    def upsert_episode_file(self, **kwargs):
        self.items[(kwargs["media_id"], kwargs["season"], kwargs["episode"])] = kwargs

    def update_path(self, *, file_id, old_path, new_path):
        for row in self.items.values():
            if row["path"] == old_path:
                row["path"] = new_path


class FakeRepos:
    def __init__(self):
        self.tasks = FakeTasks()
        self.library = FakeLibrary()

    def get_media(self, media_id):
        return {"title": "Example", "type": "tv", "year": 2024}


class FakeDrive:
    provider = "quark"

    def __init__(self, files=None):
        self.files = files or [
            ShareFile("1", "Example.S01E01.mkv", 100, "abc"),
            ShareFile("2", "Example.en.srt", 5, ""),
        ]
        self.deleted = []
        self.moved = []

    def check_share(self, share_url, password=""):
        return ShareStatus(True)

    def list_share_files(self, share_url, password=""):
        return self.files

    def transfer(self, share_url, target_dir, *, file_ids, password="", rename_map=None):
        created = [
            (item.file_id, f"{target_dir}/{item.name}", item.size, item.sha1)
            for item in self.files
            if item.file_id in file_ids
        ]
        return TransferOutcome(True, [], created, "")

    def delete_path(self, path):
        self.deleted.append(path)
        return True

    def move(self, file_id, target_dir):
        self.moved.append((file_id, target_dir))

    def rename(self, file_id, new_name):
        return None

    def list_dir(self, path):
        return []

    def list_directories(self, parent_id=""):
        return []

    def create_directory(self, parent_id="", name=""):
        return None


class FakeTargetDrive(FakeDrive):
    provider = "115"

    def __init__(self, files=None):
        super().__init__(files)
        self.remembered = []

    def remember(self, file_id, item, directory):
        self.remembered.append((file_id, directory))


class FakeCross:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def relay(
        self,
        source_key,
        source_dir,
        file_name,
        target_key,
        target_dir,
        target_name="",
        parent_task_id="",
    ):
        self.calls.append((source_key, file_name, target_key, target_dir))
        if self.fail:
            raise RuntimeError("上传目标盘失败")
        return {
            "file_id": f"t-{file_name}",
            "path": f"{target_dir}/{file_name}",
            "size": 100,
            "sha1": "landed",
            "method": "rapid",
        }


@dataclass
class Settings:
    transfer_root: str = "CSX"
    library_root: str = "Media"


def run(drive, target, cross, *, cross_paths=None):
    repos = FakeRepos()
    row = {
        "idempotency_key": "cross-key",
        "resource_id": 1,
        "media_id": 10,
        "season": 1,
        "episode": 1,
        "resource": {"provider": "quark", "share_url": "https://share.test/abc"},
    }
    result = execute_transfer(
        None,
        row,
        drives={"quark": drive, "115": target},
        repos=repos,
        settings=Settings(),
        target_provider="115",
        target_drive=target,
        target_cloud_paths=cross_paths,
        cross_service=cross,
    )
    return result, repos


def test_coerce_clamps_threads_and_concurrency():
    cfg = _coerce({"download_threads": 999, "max_concurrent": 0})
    assert cfg["download_threads"] == 16
    assert cfg["max_concurrent"] == 2  # 0 视为未填，回默认
    assert _coerce({"max_concurrent": 9})["max_concurrent"] == 4
    assert _coerce({"download_threads": "x"})["download_threads"] == 5


def test_resolve_cache_dir_falls_back_when_unwritable(tmp_path, monkeypatch):
    import csx.infra.cross_transfer as module

    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(module, "FALLBACK_CACHE_DIR", str(tmp_path / "fallback"))
    resolved = resolve_cache_dir({"cache_dir": str(blocker)})
    assert str(resolved) == str(tmp_path / "fallback")


def test_cross_transfer_relays_files_and_records_target_provider():
    drive, target, cross = FakeDrive(), FakeTargetDrive(), FakeCross()
    result, repos = run(drive, target, cross)
    assert result["ok"]
    assert len(cross.calls) == 1  # 只有视频进中继，字幕走 sidecar
    assert cross.calls[0][:3] == ("quark", "Example.S01E01.mkv", "115")
    landed = next(iter(repos.library.items.values()))
    assert landed["provider"] == "115"
    assert landed["path"].startswith("/Media")
    assert drive.deleted, "源盘中转文件应被清理"
    assert target.moved, "sidecar 应在目标盘内移动"
    assert target.remembered == [("t-Example.S01E01.mkv", "/CSX/_inbox/cross-key")], (
        "中继落盘的文件必须登记到目标盘，否则 115 移动/重命名会报「文件未登记」"
    )


def test_cross_transfer_failure_moves_task_to_retry_wait():
    result, repos = run(FakeDrive(), FakeTargetDrive(), FakeCross(fail=True))
    assert not result["ok"]
    assert result["state"] == "retry_wait"
    assert repos.tasks.transitions[-1] is TaskState.RETRY_WAIT


def test_same_provider_skips_relay():
    drive, cross = FakeDrive(), FakeCross()
    repos = FakeRepos()
    row = {
        "idempotency_key": "same-provider",
        "resource_id": 1,
        "media_id": 10,
        "season": 1,
        "episode": 1,
        "resource": {"provider": "quark", "share_url": "https://share.test/abc"},
    }
    result = execute_transfer(
        None,
        row,
        drives={"quark": drive},
        repos=repos,
        settings=Settings(),
        target_provider="quark",
        target_drive=drive,
        cross_service=cross,
    )
    assert result["ok"]
    assert cross.calls == []


def test_cross_settings_api_roundtrip(client):
    from p4_helpers import login

    login(client)
    current = client.get("/api/v1/settings/cross/config")
    assert current.status_code == 200
    data = current.json()["data"]
    assert data["download_threads"] == 5
    saved = client.post(
        "/api/v1/settings/cross/config",
        json={"enabled": False, "download_threads": 3, "max_concurrent": 1},
    )
    assert saved.status_code == 200
    assert saved.json()["data"]["enabled"] is False
    assert saved.json()["data"]["download_threads"] == 3
    bad = client.post("/api/v1/settings/cross/config", json={"library_drive": "baidu"})
    assert bad.status_code == 422
    client.post("/api/v1/settings/cross/config", json={"enabled": True, "download_threads": 5})
    client.cookies.clear()
