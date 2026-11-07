"""Drive check-in orchestration and per-account failure isolation."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class CheckinOutcome:
    account_id: int
    provider: str
    account_name: str
    checked_at: datetime
    success: bool
    reward: str
    message: str
    consecutive_days: int | None
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["checked_at"] = self.checked_at.isoformat()
        return value


def run_checkins(
    accounts: Iterable[Mapping[str, Any]],
    checkin: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    persist: Callable[[CheckinOutcome], None],
    *,
    account_id: int | None = None,
    now: datetime | None = None,
) -> list[CheckinOutcome]:
    """Run selected or all accounts; persist both successes and failures."""
    checked_at = now or datetime.now(UTC).replace(tzinfo=None)
    outcomes = []
    for account in accounts:
        identifier = int(account["id"])
        if account_id is not None and identifier != account_id:
            continue
        provider = str(account.get("provider") or "")
        name = str(account.get("name") or provider)
        try:
            result = dict(checkin(account))
            success = bool(result.get("success", True))
            message = str(result.get("message") or result.get("status") or "签到完成")
            reward_value = result.get("signin_points", result.get("points_change", ""))
            consecutive = result.get("signin_days")
            details = result
        except Exception as error:
            success = False
            message = str(error)
            reward_value = ""
            consecutive = None
            details = {"error": str(error)}
        outcome = CheckinOutcome(
            account_id=identifier,
            provider=provider,
            account_name=name,
            checked_at=checked_at,
            success=success,
            reward=str(reward_value if reward_value is not None else ""),
            message=message,
            consecutive_days=int(consecutive) if consecutive is not None else None,
            details=details,
        )
        persist(outcome)
        outcomes.append(outcome)
    return outcomes
