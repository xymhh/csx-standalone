"""Database-backed check-in runner shared by the API and daily scheduler."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.adapters.db.checkins import SqlAlchemyCheckinRepository
from csx.adapters.drive.registry import DriveRegistry
from csx.application.checkin import CheckinOutcome, run_checkins
from csx.infra.credentials import decrypt_credential
from csx.infra.models import Account, Setting
from csx.infra.side_effects import dispatch_notification_later


def source_settings(db: Session) -> dict[str, Any]:
    rows = db.scalars(select(Setting).where(Setting.key.like("sources.%")))
    return {row.key.split(".", 1)[1]: json.loads(row.value) for row in rows}


def checkin_accounts(db: Session, account_id: int | None = None) -> list[CheckinOutcome]:
    query = select(Account).order_by(Account.id)
    if account_id is not None:
        query = query.where(Account.id == account_id)
    rows = list(db.scalars(query))
    config = source_settings(db)
    repository = SqlAlchemyCheckinRepository(db)
    accounts = [
        {
            "id": row.id,
            "provider": row.provider,
            "name": row.name,
            "credential": row.credential,
        }
        for row in rows
    ]

    def invoke(account: dict[str, Any]) -> dict[str, Any]:
        credential = decrypt_credential(account["credential"])
        return DriveRegistry.checkin(account["provider"], credential, config)

    outcomes = run_checkins(accounts, invoke, repository.add, account_id=account_id)
    db.commit()
    return outcomes


def scheduled_checkin(session_factory) -> list[CheckinOutcome]:
    with session_factory() as db:
        outcomes = checkin_accounts(db)
        notify_config = {
            row.key.split(".", 1)[1]: json.loads(row.value)
            for row in db.scalars(select(Setting).where(Setting.key.like("notify.%")))
        }
    if outcomes:
        dispatch_notification_later(
            notify_config,
            "checkin_report",
            {"results": [outcome.as_dict() for outcome in outcomes]},
        )
    return outcomes
