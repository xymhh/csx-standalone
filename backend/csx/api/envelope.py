"""统一响应包络：{"ok": bool, "data": ..., "error": {...}}。"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiError(BaseModel):
    code: str
    message: str
    hint: str | None = None


class Envelope(BaseModel, Generic[T]):
    ok: bool = True
    data: T | None = None
    error: ApiError | None = None


def ok(data: Any = None) -> dict:
    return {"ok": True, "data": data, "error": None}


def fail(code: str, message: str, hint: str | None = None) -> dict:
    return {"ok": False, "data": None, "error": {"code": code, "message": message, "hint": hint}}
