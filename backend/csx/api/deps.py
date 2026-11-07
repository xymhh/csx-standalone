"""请求依赖：当前登录用户。"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from csx.application.auth import session_user
from csx.infra.db import get_db
from csx.infra.models import AdminUser

COOKIE_NAME = "csx_session"


def current_user(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    token = request.cookies.get(COOKIE_NAME, "")
    user = session_user(db, token)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "需要登录"},
        )
    return user
