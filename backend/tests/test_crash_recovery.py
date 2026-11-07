from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from csx.infra.bootstrap import recover_stale_tasks
from csx.infra.models import Base, TransferTask


def test_running_orphans_are_retried_or_dead_lettered_without_touching_other_states(
    tmp_path,
):
    engine = create_engine(f"sqlite:///{tmp_path / 'recovery.db'}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        db.add_all(
            [
                TransferTask(idempotency_key="retry", state="running", attempt=2),
                TransferTask(idempotency_key="dead", state="running", attempt=3),
                TransferTask(idempotency_key="queued", state="queued", attempt=0),
            ]
        )
        db.commit()

    assert recover_stale_tasks(sessions) == {"retry_wait": 1, "dead_letter": 1}
    with sessions() as db:
        retry = db.query(TransferTask).filter_by(idempotency_key="retry").one()
        dead = db.query(TransferTask).filter_by(idempotency_key="dead").one()
        queued = db.query(TransferTask).filter_by(idempotency_key="queued").one()
        assert retry.state == "retry_wait" and retry.next_retry_at is not None
        assert retry.last_error == "PROCESS_CRASHED_ORPHAN"
        assert dead.state == "dead_letter" and dead.dead_letter == 1
        assert dead.last_error == "PROCESS_CRASHED_ORPHAN"
        assert queued.state == "queued" and queued.last_error == ""
    engine.dispose()


def test_recovery_is_idempotent_when_no_running_tasks_remain(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    Base.metadata.create_all(engine)
    assert recover_stale_tasks(sessionmaker(bind=engine)) == {"retry_wait": 0, "dead_letter": 0}
    engine.dispose()
