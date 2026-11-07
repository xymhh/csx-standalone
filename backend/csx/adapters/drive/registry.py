"""Construct the supported vendor drives using environment credentials."""

from __future__ import annotations

import os

from sqlalchemy.orm import Session

from csx.infra.credentials import decrypt_credential
from csx.infra.models import Account


class DriveRegistry:
    @staticmethod
    def build(provider: str, credential: str) -> object:
        provider = provider.lower()
        if provider == "115":
            from csx.vendor.core.cloud import CloudDriveCapability
            from csx.vendor.drive.p115.client import P115ClientManager
            from csx.vendor.drive.p115.provider import create_p115_provider

            manager = P115ClientManager(credential)
            services = create_p115_provider(manager).services
            from .p115 import P115DriveAdapter

            return P115DriveAdapter(
                services[CloudDriveCapability.SHARE_TRANSFER],
                services[CloudDriveCapability.FILE_QUERY],
            )
        if provider == "quark":
            from csx.vendor.core.cloud import CloudDriveCapability
            from csx.vendor.drive.quark.client import QuarkClient
            from csx.vendor.drive.quark.provider import QuarkDrive, create_quark_provider

            drive = QuarkDrive(QuarkClient(cookie=credential))
            services = create_quark_provider(drive).services
            from .quark import QuarkDriveAdapter

            return QuarkDriveAdapter(
                services[CloudDriveCapability.SHARE_TRANSFER],
                services[CloudDriveCapability.FILE_QUERY],
            )
        raise ValueError(f"unsupported drive provider: {provider}")

    @classmethod
    def from_session(cls, db: Session) -> dict[str, object]:
        return {
            account.provider: cls.build(account.provider, decrypt_credential(account.credential))
            for account in db.query(Account).all()
            if account.provider in {"115", "quark"}
        }

    @staticmethod
    def from_environment() -> dict[str, object]:
        result = {}
        cookie = os.getenv("CSX_115_COOKIE", "").strip()
        if cookie:
            result["115"] = DriveRegistry.build("115", cookie)
        quark_cookie = os.getenv("CSX_QUARK_COOKIE", "").strip()
        if quark_cookie:
            result["quark"] = DriveRegistry.build("quark", quark_cookie)
        return result

    @staticmethod
    def checkin(provider: str, credential: str, config: dict | None = None) -> dict:
        """Run the vendor's native check-in operation behind the drive boundary."""
        provider = provider.lower()
        config = config or {}
        if provider == "115":
            from csx.vendor.drive.p115.client import P115ClientManager

            manager = P115ClientManager(credential)
            return manager.checkin(str(config.get("p115_checkin_mode") or "normal"))
        if provider == "quark":
            from csx.vendor.drive.quark.client import QuarkClient

            checkin_url = str(
                config.get("quark_checkin_url") or config.get("_quark_checkin_url") or ""
            )
            client = QuarkClient(cookie=credential, checkin_url=checkin_url)
            try:
                return client.checkin("normal")
            finally:
                client.close()
        raise ValueError(f"unsupported check-in provider: {provider}")
