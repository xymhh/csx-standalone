from csx.application.transfer import execute_transfer
from csx.domain.task import TaskState
from csx.ports.drive import ShareStatus, TransferOutcome


class FakeDrive:
    def check_share(self, share_url, password=""):
        return ShareStatus(True)

    def transfer(self, share_url, target_dir, *, file_ids, password="", rename_map=None):
        assert share_url == "https://share.example/link"
        assert target_dir == "/Movies"
        assert file_ids == ["video-1"]
        assert password == "abcd"
        return TransferOutcome(True, created=[("landed-1", "/Movies/video.mkv", 100, "sha1")])


class FakeTasks:
    def __init__(self):
        self.state = TaskState.QUEUED.value
        self.attempt = 0

    def create_or_get(self, *_args, **_kwargs):
        return 1, False

    def get(self, _task_id):
        return {"state": self.state, "attempt": self.attempt}

    def transition(self, _task_id, state, *, error=""):
        self.state = state.value
        self.attempt += int(state is TaskState.RUNNING)


class FakeRepos:
    def __init__(self):
        self.tasks = FakeTasks()
        self.library = object()


class FakeSettings:
    transfer_root = "CSX"


def test_manual_task_transfers_selected_files_directly_to_target_folder():
    repos = FakeRepos()
    resource = {
        "manual_transfer": True,
        "provider": "quark",
        "share_url": "https://share.example/link",
        "password": "abcd",
        "file_ids": ["video-1"],
        "target_dir": "/Movies",
        "media_id": None,
    }

    result = execute_transfer(
        None,
        {"id": 1, "idempotency_key": "manual-1", "resource": resource, "attempt": 1},
        drives={"quark": FakeDrive()},
        repos=repos,
        settings=FakeSettings(),
    )

    assert result["ok"] is True
    assert result["manual"] is True
    assert result["target_dir"] == "/Movies"
    assert repos.tasks.state == TaskState.SUCCEEDED.value
