"""设置、网盘账号、系统自检与事件流 API（原 routes/resources.py 拆分）。"""

from __future__ import annotations

import asyncio
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.adapters.drive.registry import DriveRegistry
from csx.api.envelope import ok
from csx.api.routes.resource_common import _raise
from csx.application.notify_template import normalize_templates
from csx.domain.category import default_strategies
from csx.infra.category_config import normalize_strategies
from csx.infra.credentials import decrypt_credential, encrypt_credential
from csx.infra.db import SessionLocal, get_db
from csx.infra.drive_runtime import drive_for
from csx.infra.events import event_bus
from csx.infra.models import (
    Account,
    Setting,
)
from csx.infra.settings import settings

settings_api = APIRouter(prefix="/settings", tags=["settings"])
accounts = APIRouter(prefix="/accounts", tags=["accounts"])
doctor = APIRouter(prefix="/doctor", tags=["doctor"])
events = APIRouter(prefix="/events", tags=["events"])


class AccountIn(BaseModel):
    provider: str = Field(min_length=1, max_length=32)
    credential: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=128)
    is_enabled: bool = True
    is_primary: bool = False
    transfer_path: str = Field(default="/CSX/_inbox", max_length=256)
    media_path: str = Field(default="/CSX/媒体库", max_length=256)


class AccountPatch(BaseModel):
    credential: str | None = Field(default=None, min_length=1)
    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_enabled: bool | None = None
    is_primary: bool | None = None
    transfer_path: str | None = Field(default=None, max_length=256)
    media_path: str | None = Field(default=None, max_length=256)


class QrcodeStartRequest(BaseModel):
    provider: Literal["115", "quark"]


class QrcodeCheckRequest(BaseModel):
    provider: Literal["115", "quark"]
    token_data: dict[str, Any]
    name: str = Field(default="我的115账号", min_length=1, max_length=128)
    auto_save: bool = True


SECTIONS = {"baseline", "sources", "transfer", "strm", "notify", "advanced", "category"}


HEARTBEAT_SECONDS = 15


def _apply_defaults(section: str, values: dict[str, Any]) -> dict[str, Any]:
    """给缺省项补上默认值，方便前端直接渲染（不写库）。"""
    if section == "category":
        values.setdefault("enabled", True)
        values.setdefault("movie", default_strategies("movie"))
        values.setdefault("tv", default_strategies("tv"))
    elif section == "notify":
        values["templates"] = normalize_templates(values.get("templates"))
    return values


@settings_api.get("")
def all_settings(db: Session = Depends(get_db)):
    values = {section: {} for section in sorted(SECTIONS)}
    for row in db.scalars(select(Setting)):
        section, separator, key = row.key.partition(".")
        if separator and section in SECTIONS:
            values[section][key] = json.loads(row.value)
    for section in SECTIONS:
        values[section] = _apply_defaults(section, values[section])
    return ok(values)


@settings_api.get("/{section}")
def get_settings(section: str, db: Session = Depends(get_db)):
    if section not in SECTIONS:
        _raise(404, "INVALID_SECTION", "设置分组不存在")
    values = {}
    for row in db.scalars(select(Setting).where(Setting.key.like(f"{section}.%"))):
        values[row.key.split(".", 1)[1]] = json.loads(row.value)
    return ok(_apply_defaults(section, values))


@settings_api.put("/{section}")
def put_settings(section: str, body: dict[str, Any], db: Session = Depends(get_db)):
    if section not in SECTIONS:
        _raise(404, "INVALID_SECTION", "设置分组不存在")
    if section == "category":
        for key in ("movie", "tv"):
            if key in body:
                body[key] = normalize_strategies(body[key])
    if section == "notify" and "templates" in body:
        body["templates"] = normalize_templates(body["templates"])
        for template in body["templates"].values():
            if len(template) > 4000:
                _raise(422, "TEMPLATE_TOO_LONG", "通知模板不能超过 4000 个字符")
    for key, value in body.items():
        if not key or "." in key:
            _raise(422, "INVALID_SETTING_KEY", "配置项名称无效")
        setting = db.get(Setting, f"{section}.{key}")
        if setting is None:
            setting = Setting(key=f"{section}.{key}", value=json.dumps(value, ensure_ascii=False))
            db.add(setting)
        else:
            setting.value = json.dumps(value, ensure_ascii=False)
            setting.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return get_settings(section, db)


def _drive_for(request: Request, db: Session, provider: str):
    drive = drive_for(db, provider, getattr(request.app.state, "drives", {}))
    if drive is None:
        _raise(404, "ACCOUNT_NOT_FOUND", f"未配置 {provider} 网盘账号")
    return drive


@settings_api.post("/test/{provider}")
def test_provider(provider: str, request: Request, db: Session = Depends(get_db)):
    try:
        _drive_for(request, db, provider.lower()).list_dir("/")
        return ok({"valid": True, "provider": provider, "message": "连通正常"})
    except Exception as error:
        return ok({"valid": False, "provider": provider, "message": str(error)})


def _account_data(row: Account) -> dict:
    info = {}
    try:
        if row.quota_state:
            info = json.loads(row.quota_state)
    except Exception:
        info = {}
    return {
        "id": row.id,
        "provider": row.provider,
        "name": row.name,
        "is_enabled": getattr(row, "is_enabled", True),
        "is_primary": getattr(row, "is_primary", False),
        "transfer_path": getattr(row, "transfer_path", "/CSX/_inbox"),
        "media_path": getattr(row, "media_path", "/CSX/媒体库"),
        "has_credential": bool(row.credential),
        "masked": "***" if row.credential else "",
        "info": info,
    }


@accounts.post("/qrcode/start")
def start_account_qrcode(body: QrcodeStartRequest):
    try:
        return ok(DriveRegistry.create_qrcode(body.provider))
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "QRCODE_START_FAILED", "message": str(error)},
        ) from error


@accounts.post("/qrcode/check")
def check_account_qrcode(
    body: QrcodeCheckRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        result = DriveRegistry.check_qrcode(body.provider, body.token_data)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail={"code": "QRCODE_CHECK_FAILED", "message": str(error)},
        ) from error

    status = result["status"]
    account_data = None
    if status == "success":
        cookie = result.get("cookie")
        if not cookie:
            raise HTTPException(
                status_code=502,
                detail={"code": "QRCODE_COOKIE_MISSING", "message": "扫码成功但未获得账号凭据"},
            )
        if body.auto_save:
            if not body.name.strip():
                _raise(422, "INVALID_ACCOUNT_NAME", "账号备注名称不能为空")
            try:
                encrypted = encrypt_credential(cookie)
            except RuntimeError as error:
                _raise(503, "SECRET_KEY_REQUIRED", str(error))
            # 同类首个账号设为 primary
            has_same = (
                db.scalar(select(Account).where(Account.provider == body.provider)) is not None
            )
            account = Account(
                provider=body.provider,
                name=body.name.strip(),
                credential=encrypted,
                is_enabled=True,
                is_primary=not has_same,
            )
            db.add(account)
            db.commit()
            db.refresh(account)
            account_data = _account_data(account)
            getattr(request.app.state, "drives", {}).pop(body.provider, None)

    return ok(
        {
            "status": status,
            "message": "绑定成功" if status == "success" and body.auto_save else result["message"],
            "account": account_data,
        }
    )


@accounts.get("")
def list_accounts(db: Session = Depends(get_db)):
    rows = db.scalars(select(Account).order_by(Account.id))
    return ok([_account_data(row) for row in rows])


@accounts.post("")
def create_account(body: AccountIn, db: Session = Depends(get_db)):
    provider = body.provider.lower()
    if provider not in {"115", "quark"}:
        _raise(422, "UNSUPPORTED_PROVIDER", "目前支持 115 和 quark")
    try:
        credential = encrypt_credential(body.credential)
    except RuntimeError as error:
        _raise(503, "SECRET_KEY_REQUIRED", str(error))
    has_same = db.scalar(select(Account).where(Account.provider == provider)) is not None
    row = Account(
        provider=provider,
        credential=credential,
        name=body.name,
        is_enabled=body.is_enabled,
        is_primary=body.is_primary if has_same else True,
        transfer_path=body.transfer_path,
        media_path=body.media_path,
    )
    if row.is_primary:
        # 其他同类账号取消 primary
        for other in db.scalars(select(Account).where(Account.provider == provider)).all():
            other.is_primary = False
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(_account_data(row))


@accounts.patch("/{account_id}")
def update_account(
    account_id: int,
    body: AccountPatch,
    request: Request,
    db: Session = Depends(get_db),
):
    row = db.get(Account, account_id)
    if row is None:
        _raise(404, "ACCOUNT_NOT_FOUND", "账号不存在")
    values = body.model_dump(exclude_unset=True)
    if values.get("name") is not None:
        row.name = values["name"]
    if values.get("is_enabled") is not None:
        row.is_enabled = values["is_enabled"]
    if values.get("transfer_path") is not None:
        row.transfer_path = values["transfer_path"]
    if values.get("media_path") is not None:
        row.media_path = values["media_path"]
    if values.get("is_primary") is not None and values["is_primary"]:
        # 取消同类其他主号
        for other in db.scalars(select(Account).where(Account.provider == row.provider)).all():
            other.is_primary = False
        row.is_primary = True
    elif values.get("is_primary") is not None:
        row.is_primary = False
    if values.get("credential") is not None:
        try:
            row.credential = encrypt_credential(values["credential"])
        except RuntimeError as error:
            _raise(503, "SECRET_KEY_REQUIRED", str(error))
    db.commit()
    getattr(request.app.state, "drives", {}).pop(row.provider, None)
    return ok(_account_data(row))


@accounts.delete("/{account_id}")
def delete_account(account_id: int, request: Request, db: Session = Depends(get_db)):
    row = db.get(Account, account_id)
    if row is None:
        _raise(404, "ACCOUNT_NOT_FOUND", "账号不存在")
    provider = row.provider
    db.delete(row)
    db.commit()
    getattr(request.app.state, "drives", {}).pop(provider, None)
    return ok({"deleted": True})


@accounts.post("/{account_id}/test")
def test_account(account_id: int, request: Request, db: Session = Depends(get_db)):
    row = db.get(Account, account_id)
    if row is None:
        _raise(404, "ACCOUNT_NOT_FOUND", "账号不存在")
    try:
        drive = getattr(request.app.state, "drives", {}).get(row.provider)
        if drive is None:
            credential = decrypt_credential(row.credential)
            drive = DriveRegistry.build(row.provider, credential)
        drive.list_dir("/")

        info = {}
        try:
            credential = decrypt_credential(row.credential)
            info = DriveRegistry.get_account_profile(row.provider, credential)
            if info:
                row.quota_state = json.dumps(info, ensure_ascii=False)
                db.commit()
        except Exception:
            pass

        return ok({"valid": True, "provider": row.provider, "message": "连通正常", "info": info})
    except Exception as error:
        return ok({"valid": False, "provider": row.provider, "message": str(error)})


@doctor.get("")
def diagnose(request: Request, probe: bool = False):
    db_ok = False
    db_error = ""
    db_size = 0
    try:
        with SessionLocal() as db:
            db.execute(select(1))
            db_ok = True
        db_path = settings.data_dir / "csx.db"
        db_size = db_path.stat().st_size if db_path.exists() else 0
    except Exception as error:
        db_error = str(error)
    data_path = Path(settings.data_dir)
    try:
        disk = shutil.disk_usage(data_path)
        writable = data_path.is_dir() and bool(data_path.stat().st_mode & 0o222)
        disk_result = {"total": disk.total, "free": disk.free, "writable": writable}
    except OSError as error:
        disk_result = {"error": str(error), "writable": False}
    scheduler = getattr(request.app.state, "scheduler", None)
    account_checks = []
    try:
        with SessionLocal() as db:
            accounts = list(db.scalars(select(Account)))
    except Exception as error:
        accounts = []
        account_checks = [{"error": str(error)}]

    def _account_snapshot(account: Account) -> dict:
        return {
            "provider": account.provider,
            "configured": True,
            "valid": None,
            "message": "",
            "quota": json.loads(account.quota_state or "{}"),
        }

    def _check_account(account: Account) -> dict:
        drive = getattr(request.app.state, "drives", {}).get(account.provider)
        if drive is None:
            return {"provider": account.provider, "configured": True, "valid": False}
        try:
            drive.list_dir("/")
            valid, message = True, ""
        except Exception as exc:
            valid = False
            message = str(exc)
        return {
            "provider": account.provider,
            "configured": True,
            "valid": valid,
            "message": message,
            "quota": json.loads(account.quota_state or "{}"),
        }

    if accounts and not probe:
        # 默认只回配置快照：网盘目录探测在海外节点可达 50s+，不能挂在每次首页自检里
        account_checks.extend(_account_snapshot(account) for account in accounts)
    elif accounts:
        pool = ThreadPoolExecutor(max_workers=min(4, len(accounts)))
        try:
            futures = [(account, pool.submit(_check_account, account)) for account in accounts]
            for account, future in futures:
                try:
                    account_checks.append(future.result(timeout=60))
                except Exception:
                    account_checks.append(
                        {
                            "provider": account.provider,
                            "configured": True,
                            "valid": None,
                            "message": "探测超时，网盘接口无响应",
                        }
                    )
        finally:
            pool.shutdown(wait=False)
    from csx.adapters.media.tmdb import TmdbClient

    return ok(
        {
            "database": {"ok": db_ok, "size_bytes": db_size, "error": db_error},
            "accounts": account_checks,
            "scheduler": {
                "running": bool(scheduler and scheduler.running),
                "active_workers": scheduler.active_workers if scheduler else 0,
                "waiting_queue_depth": scheduler.waiting_queue_depth if scheduler else 0,
            },
            "disk": disk_result,
            "tmdb": TmdbClient.diagnose(),
        }
    )


@events.get("")
async def event_stream():
    async def generate():
        async with event_bus.subscribe() as queue:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except TimeoutError:
                    event = {"type": "heartbeat", "data": {"at": datetime.now(UTC).isoformat()}}
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )
