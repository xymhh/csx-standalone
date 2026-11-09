"""Persistence helpers for the Telegram scan cursor stored in the Setting table."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from csx.infra.models import Setting

SCAN_STATE_KEY = "tg.scan_state"


def _empty_state() -> dict[str, Any]:
    return {"channels": {}, "last_scan_at": None, "last_error": None}


def load_state(session: Session) -> dict[str, Any]:
    row = session.get(Setting, SCAN_STATE_KEY)
    if row is None:
        return _empty_state()
    try:
        value = json.loads(row.value)
    except (TypeError, json.JSONDecodeError):
        return _empty_state()
    if not isinstance(value, dict):
        return _empty_state()
    state = _empty_state()
    state.update(value)
    if not isinstance(state.get("channels"), dict):
        state["channels"] = {}
    return state


def save_state(session: Session, state: dict[str, Any]) -> None:
    payload = json.dumps(state, ensure_ascii=False)
    row = session.get(Setting, SCAN_STATE_KEY)
    if row is None:
        session.add(Setting(key=SCAN_STATE_KEY, value=payload))
    else:
        row.value = payload
    session.flush()
