"""登录 / 登出 / 当前用户 / 改密。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from csx.api.deps import COOKIE_NAME, current_user
from csx.api.envelope import ok
from csx.application import auth as auth_service
from csx.infra.db import get_db
from csx.infra.models import AdminUser
from csx.infra.ratelimit import is_blocked, record_failure, reset
from csx.infra.settings import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class PasswordIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = _client_ip(request)
    if is_blocked(ip):
        raise HTTPException(
            status_code=429,
            detail={"code": "TOO_MANY_ATTEMPTS", "message": "尝试过于频繁，请稍后再试"},
        )

    user = auth_service.authenticate(db, body.username, body.password)
    if user is None:
        record_failure(ip)
        raise HTTPException(
            status_code=401, detail={"code": "BAD_CREDENTIALS", "message": "用户名或密码错误"}
        )

    reset(ip)
    token = auth_service.create_session(db, user, ip, request.headers.get("user-agent", ""))
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return ok({"username": user.username})


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    auth_service.revoke_session(db, request.cookies.get(COOKIE_NAME, ""))
    response.delete_cookie(COOKIE_NAME, path="/")
    return ok(None)


@router.get("/me")
def me(user: AdminUser = Depends(current_user)):
    return ok({"username": user.username})


@router.post("/password")
def change_password(
    body: PasswordIn,
    response: Response,
    user: AdminUser = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not auth_service.change_password(db, user, body.old_password, body.new_password):
        raise HTTPException(
            status_code=400, detail={"code": "BAD_OLD_PASSWORD", "message": "原密码不正确"}
        )
    response.delete_cookie(COOKIE_NAME, path="/")
    return ok({"changed": True})
