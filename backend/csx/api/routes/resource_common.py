"""resources 拆分后的共享小工具（分页与统一抛错）。"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session


def _raise(status: int, code: str, message: str) -> None:
    raise HTTPException(status, detail={"code": code, "message": message})


def _page(db: Session, query, page: int, page_size: int):
    if page < 1 or page_size < 1 or page_size > 200:
        _raise(422, "VALIDATION_ERROR", "分页参数无效")
    result = db.execute(query.offset((page - 1) * page_size).limit(page_size))
    if len(query.column_descriptions) == 1:
        return result.scalars().all()
    return result.all()
