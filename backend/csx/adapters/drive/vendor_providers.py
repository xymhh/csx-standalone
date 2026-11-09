"""Vendor 网盘 provider 构造：跨盘中继需要上传/秒传/下载能力。

只在这里接触 ``csx.vendor``，其他层通过本模块拿已构造好的 provider。
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from csx.infra.credentials import decrypt_credential
from csx.infra.models import Account

SUPPORTED_PROVIDERS = ("115", "quark")


def enabled_accounts(db: Session) -> dict[str, Account]:
    """provider → 启用中的首选账号（is_primary 优先，其次 id 小的）。"""
    accounts = db.scalars(
        select(Account)
        .where(Account.is_enabled.is_(True))
        .order_by(Account.is_primary.desc(), Account.id.asc())
    ).all()
    picked: dict[str, Account] = {}
    for account in accounts:
        provider = str(account.provider or "").lower()
        if provider in SUPPORTED_PROVIDERS and provider not in picked:
            picked[provider] = account
    return picked


def build_provider(provider: str, credential: str) -> Any:
    """构造 vendor 的 CloudDriveProvider（含上传/秒传/下载能力）。"""
    provider = provider.lower()
    if provider == "115":
        from csx.vendor.drive.p115.client import P115ClientManager
        from csx.vendor.drive.p115.provider import create_p115_provider

        return create_p115_provider(P115ClientManager(credential))
    if provider == "quark":
        from csx.vendor.drive.quark.client import QuarkClient
        from csx.vendor.drive.quark.provider import QuarkDrive, create_quark_provider

        return create_quark_provider(QuarkDrive(QuarkClient(cookie=credential)))
    raise ValueError(f"不支持的网盘：{provider}")


def build_all(db: Session) -> dict[str, Any]:
    providers: dict[str, Any] = {}
    for provider, account in enabled_accounts(db).items():
        try:
            providers[provider] = build_provider(provider, decrypt_credential(account.credential))
        except Exception as error:  # 单个账号构造失败不影响其他盘
            logging.getLogger(__name__).warning(f"构造 {provider} 跨盘 provider 失败：{error}")
    return providers
