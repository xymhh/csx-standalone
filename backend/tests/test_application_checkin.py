from datetime import UTC, datetime

from csx.application.checkin import run_checkins
from csx.infra.scheduler import TaskScheduler


def test_checkin_runs_all_accounts_and_records_failure_without_aborting():
    accounts = [
        {"id": 1, "provider": "115", "name": "One"},
        {"id": 2, "provider": "quark", "name": "Two"},
    ]
    persisted = []

    def checkin(account):
        if account["id"] == 2:
            raise RuntimeError("offline")
        return {"success": True, "signin_points": 8, "signin_days": 5, "message": "ok"}

    outcomes = run_checkins(
        accounts,
        checkin,
        persisted.append,
        now=datetime(2026, 11, 8, 0, 30, tzinfo=UTC),
    )
    assert len(outcomes) == 2
    assert [outcome.success for outcome in outcomes] == [True, False]
    assert outcomes[0].reward == "8" and outcomes[0].consecutive_days == 5
    assert outcomes[1].message == "offline"
    assert persisted == outcomes


def test_checkin_can_select_one_account():
    outcomes = run_checkins(
        [{"id": 1, "provider": "115"}, {"id": 2, "provider": "quark"}],
        lambda account: {"success": True, "message": account["provider"]},
        lambda _outcome: None,
        account_id=2,
    )
    assert len(outcomes) == 1 and outcomes[0].account_id == 2


def test_daily_checkin_scheduler_targets_local_0030():
    before = datetime(2026, 11, 8, 0, 0)
    after = datetime(2026, 11, 8, 0, 31)
    assert TaskScheduler.seconds_until_daily_checkin(before) == 30 * 60
    assert TaskScheduler.seconds_until_daily_checkin(after) == (23 * 60 + 59) * 60
