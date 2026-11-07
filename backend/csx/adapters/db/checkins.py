"""SQLAlchemy persistence for check-in history."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.application.checkin import CheckinOutcome
from csx.infra.models import CheckinRecord


class SqlAlchemyCheckinRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, outcome: CheckinOutcome) -> CheckinRecord:
        row = CheckinRecord(
            account_id=outcome.account_id,
            provider=outcome.provider,
            account_name=outcome.account_name,
            checked_at=outcome.checked_at,
            success=outcome.success,
            reward=outcome.reward,
            message=outcome.message,
            consecutive_days=outcome.consecutive_days,
            details=json.dumps(outcome.details, ensure_ascii=False),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def list(self, *, account_id: int | None = None, limit: int = 100) -> list[CheckinRecord]:
        query = select(CheckinRecord).order_by(
            CheckinRecord.checked_at.desc(), CheckinRecord.id.desc()
        )
        if account_id is not None:
            query = query.where(CheckinRecord.account_id == account_id)
        return list(self.session.scalars(query.limit(min(500, max(1, limit)))))
