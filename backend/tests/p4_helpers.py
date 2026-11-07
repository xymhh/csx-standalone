from __future__ import annotations

import os
import uuid

from csx.infra.db import SessionLocal
from csx.infra.models import MediaItem


def login(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": os.getenv("CSX_ADMIN_USER", "admin"),
            "password": os.environ["CSX_ADMIN_PASSWORD"],
        },
    )
    assert response.status_code == 200
    return response


def media_row():
    with SessionLocal() as db:
        tmdb_id = int(uuid.uuid4().int % 2_000_000_000) + 1
        row = MediaItem(tmdb_id=tmdb_id, type="tv", title=f"P4-{uuid.uuid4().hex[:8]}")
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
