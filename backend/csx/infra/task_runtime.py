"""Persistence operations for API task controls."""

from __future__ import annotations

from sqlalchemy.orm import Session

from csx.adapters.db.repositories import SqlAlchemyTaskRepository
from csx.domain.task import TaskState


def create_or_get_task(
    db: Session,
    idempotency_key: str,
    *,
    subscription_id: int | None,
    resource_id: int | None,
) -> tuple[int, bool]:
    return SqlAlchemyTaskRepository(db).create_or_get(
        idempotency_key,
        subscription_id=subscription_id,
        resource_id=resource_id,
    )


def transition_task(db: Session, task_id: int, state: TaskState, *, error: str = "") -> TaskState:
    return SqlAlchemyTaskRepository(db).transition(task_id, state, error=error)
