from __future__ import annotations

from dataclasses import dataclass

from csx.application.transfer import execute_transfer
from csx.domain.task import TaskState, assert_transition
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
        assert_transition(row["state"], dst)
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
        identity = (kwargs["media_id"], kwargs["season"], kwargs["episode"])
        self.items[identity] = kwargs

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

    def __init__(self, *, valid=True, partial=False, organize_fails=False):
        self.valid = valid
        self.partial = partial
        self.organize_fails = organize_fails
        self.transfers = 0
        self.files = [
            ShareFile("1", "Example.S01E01.mkv", 100, "abc"),
            ShareFile("2", "Example.en.srt", 5, ""),
        ]

    def check_share(self, share_url, password=""):
        return ShareStatus(self.valid, "expired" if not self.valid else "")

    def list_share_files(self, share_url, password=""):
        return self.files

    def transfer(self, share_url, target_dir, *, file_ids, password="", rename_map=None):
        self.transfers += 1
        created = [
            (item.file_id, f"{target_dir}/{item.name}", item.size, item.sha1)
            for item in self.files
            if item.file_id in file_ids
        ]
        return TransferOutcome(
            not self.partial,
            ["2"] if self.partial else [],
            created,
            "partial" if self.partial else "",
        )

    def move(self, file_id, target_dir):
        if self.organize_fails:
            raise RuntimeError("move failed")

    def rename(self, file_id, new_name):
        if self.organize_fails:
            raise RuntimeError("rename failed")

    def list_dir(self, path):
        return []


@dataclass
class Settings:
    transfer_root: str = "CSX"
    library_root: str = "Media"


def run(drive, *, key="task-key", episode=1):
    repos = FakeRepos()
    row = {
        "idempotency_key": key,
        "resource_id": 1,
        "media_id": 10,
        "season": 1,
        "episode": episode,
        "resource": {"provider": "quark", "share_url": "https://share.test/abc"},
    }
    result = execute_transfer(None, row, drives={"quark": drive}, repos=repos, settings=Settings())
    return result, repos


def test_transfer_single_episode_and_sidecar_does_not_add_episode():
    result, repos = run(FakeDrive())
    assert result["ok"] and result["organized"]
    assert len(repos.library.items) == 1
    assert next(iter(repos.library.items.values()))["episode"] == 1


def test_partial_transfer_moves_task_to_retry_wait():
    result, repos = run(FakeDrive(partial=True))
    assert result["state"] == "retry_wait"
    assert repos.tasks.transitions[-1] is TaskState.RETRY_WAIT
    assert repos.library.items


def test_expired_share_goes_to_dead_letter():
    result, repos = run(FakeDrive(valid=False))
    assert result["state"] == "dead_letter"
    assert repos.tasks.transitions[-1] is TaskState.DEAD_LETTER


def test_organize_failure_keeps_transferred_file_and_task_succeeds():
    result, repos = run(FakeDrive(organize_fails=True))
    assert result["ok"] and not result["organized"]
    assert repos.library.items
    assert repos.tasks.transitions[-1] is TaskState.SUCCEEDED


def test_same_idempotency_key_only_transfers_once():
    drive, repos = FakeDrive(), FakeRepos()
    row = {
        "idempotency_key": "same",
        "resource_id": 1,
        "media_id": 10,
        "season": 1,
        "episode": 1,
        "resource": {"provider": "quark", "share_url": "url"},
    }
    drives = {"quark": drive}
    execute_transfer(None, row, drives=drives, repos=repos, settings=Settings())
    again = execute_transfer(None, row, drives=drives, repos=repos, settings=Settings())
    assert again["idempotent"]
    assert drive.transfers == 1


def test_duplicate_episode_identity_does_not_depend_on_filename():
    drive, repos = FakeDrive(), FakeRepos()
    row = {
        "idempotency_key": "first",
        "resource_id": 1,
        "media_id": 10,
        "season": 1,
        "episode": 1,
        "resource": {"provider": "quark", "share_url": "url"},
    }
    execute_transfer(None, row, drives={"quark": drive}, repos=repos, settings=Settings())
    repos.library.upsert_episode_file(
        media_id=10, season=1, episode=1, path="another-name.mkv", size=50, sha1="xyz"
    )
    assert len(repos.library.items) == 1
    assert repos.library.items[(10, 1, 1)]["path"] == "another-name.mkv"
