from csx.application.transfer import execute_transfer
from csx.domain.task import TaskState, assert_transition
from csx.ports.drive import ShareFile, ShareStatus, TransferOutcome


class FakeTasks:
    def __init__(self):
        self.state = TaskState.QUEUED
        self.attempt = 0

    def create_or_get(self, _key, **_kwargs):
        return 1, True

    def transition(self, _task_id, target, *, error=""):
        assert_transition(self.state, target)
        self.state = target
        self.attempt += target is TaskState.RUNNING
        self.error = error

    def get(self, _task_id):
        return {"state": self.state.value, "attempt": self.attempt}


class FakeLibrary:
    def __init__(self, quality):
        self.existing = {"quality_bucket": quality}
        self.upserted = []

    def get_episode_file(self, **_kwargs):
        return self.existing

    def upsert_episode_file(self, **kwargs):
        self.upserted.append(kwargs)

    def update_path(self, **_kwargs):
        pass


class FakeDrive:
    provider = "115"

    def __init__(self):
        self.transfers = 0

    def check_share(self, *_args):
        return ShareStatus(True)

    def list_share_files(self, *_args):
        return [ShareFile("f1", "Show.S01E01.mkv")]

    def transfer(self, *_args, **_kwargs):
        self.transfers += 1
        return TransferOutcome(True, created=[("f1", "inbox/Show.S01E01.mkv", 10, "sha")])

    def move(self, *_args):
        pass

    def rename(self, *_args):
        pass


class FakeRepos:
    def __init__(self, quality):
        self.tasks = FakeTasks()
        self.library = FakeLibrary(quality)
        self.ignored = None

    def get_resource(self, _resource_id):
        return {
            "provider": "115",
            "share_url": "https://share.test/a",
            "media_id": 1,
            "season": 1,
            "episode": 1,
            "quality_bucket": "hd",
            "upgrade_enabled": True,
        }

    def get_media(self, _media_id):
        return {"title": "Show", "type": "tv", "year": None}

    def ignore_resource(self, _resource_id, state):
        self.ignored = state


class Settings:
    transfer_root = "CSX"
    library_root = "Media"


def run(existing_quality):
    drive = FakeDrive()
    repos = FakeRepos(existing_quality)
    result = execute_transfer(
        None,
        {"idempotency_key": "k", "resource_id": 1, "media_id": 1},
        drives={"115": drive},
        repos=repos,
        settings=Settings(),
    )
    return result, repos, drive


def test_better_candidate_transfers_and_marks_upgrade():
    result, repos, drive = run("sd")
    assert result["ok"] and result["is_upgrade"]
    assert result["existing_bucket"] == "sd" and result["quality_bucket"] == "hd"
    assert drive.transfers == 1
    assert repos.tasks.state is TaskState.SUCCEEDED


def test_equal_or_lower_candidate_is_ignored_without_transfer():
    result, repos, drive = run("hdr")
    assert result["candidate_state"] == "ignored_low_quality"
    assert repos.ignored == "ignored_low_quality"
    assert drive.transfers == 0
    assert repos.tasks.state is TaskState.CANCELLED
