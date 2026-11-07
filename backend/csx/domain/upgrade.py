"""Pure quality ranking and wash-upgrade decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

QUALITY_RANK: dict[str, int] = {
    "remux": 6,
    "dv": 5,
    "hdr": 4,
    "4k": 3,
    "hd": 2,
    "sd": 1,
    "unknown": 0,
}


class UpgradeAction(StrEnum):
    UPGRADE = "upgrade"
    IGNORED_LOW_QUALITY = "ignored_low_quality"
    UPGRADE_DISABLED = "upgrade_disabled"


@dataclass(frozen=True)
class UpgradeDecision:
    action: UpgradeAction
    existing_bucket: str
    candidate_bucket: str

    @property
    def is_upgrade(self) -> bool:
        return self.action is UpgradeAction.UPGRADE

    @property
    def accepted(self) -> bool:
        return self.action is UpgradeAction.UPGRADE


def quality_rank(bucket: str | None) -> int:
    """Return the configured rank; unknown or missing labels map to zero."""
    return QUALITY_RANK.get(str(bucket or "unknown").strip().lower(), 0)


def compare_quality(existing: str | None, candidate: str | None) -> int:
    """Compare candidate quality to the existing file: positive means better."""
    return quality_rank(candidate) - quality_rank(existing)


def decide_upgrade(
    existing_bucket: str | None,
    candidate_bucket: str | None,
    *,
    upgrade_enabled: bool = True,
) -> UpgradeDecision:
    """Decide whether a candidate can replace the file already in the library."""
    existing = str(existing_bucket or "unknown").strip().lower()
    candidate = str(candidate_bucket or "unknown").strip().lower()
    if not upgrade_enabled:
        action = UpgradeAction.UPGRADE_DISABLED
    elif compare_quality(existing, candidate) > 0:
        action = UpgradeAction.UPGRADE
    else:
        action = UpgradeAction.IGNORED_LOW_QUALITY
    return UpgradeDecision(action, existing, candidate)
