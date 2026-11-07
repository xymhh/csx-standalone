import pytest

from csx.domain.upgrade import (
    QUALITY_RANK,
    UpgradeAction,
    compare_quality,
    decide_upgrade,
    quality_rank,
)


def test_quality_ladder_is_ordered():
    assert QUALITY_RANK == {
        "remux": 6,
        "dv": 5,
        "hdr": 4,
        "4k": 3,
        "hd": 2,
        "sd": 1,
        "unknown": 0,
    }
    assert [quality_rank(name) for name in ("remux", "dv", "hdr", "4k", "hd", "sd", "?")] == [
        6,
        5,
        4,
        3,
        2,
        1,
        0,
    ]


@pytest.mark.parametrize(
    ("existing", "candidate", "action"),
    [
        ("sd", "hd", UpgradeAction.UPGRADE),
        ("4k", "remux", UpgradeAction.UPGRADE),
        ("hdr", "hdr", UpgradeAction.IGNORED_LOW_QUALITY),
        ("remux", "4k", UpgradeAction.IGNORED_LOW_QUALITY),
    ],
)
def test_wash_upgrade_matrix(existing, candidate, action):
    assert decide_upgrade(existing, candidate).action is action


def test_quality_comparison_and_disabled_upgrade():
    assert compare_quality("unknown", "sd") == 1
    decision = decide_upgrade("sd", "remux", upgrade_enabled=False)
    assert decision.action is UpgradeAction.UPGRADE_DISABLED
    assert not decision.is_upgrade
