"""Construct the supported vendor drives using environment credentials."""

from __future__ import annotations

import os
from base64 import b64encode
from io import BytesIO

from sqlalchemy.orm import Session

from csx.infra.credentials import decrypt_credential
from csx.infra.models import Account


class DriveRegistry:
    @staticmethod
    def create_qrcode(provider: str) -> dict:
        """Create a provider QR login session and normalize its browser payload."""
        provider = provider.strip().lower()
        if provider == "115":
            from csx.vendor.drive.p115.client import P115ClientManager

            result = P115ClientManager.create_qrcode_login("alipaymini")
            token_data = {
                key: str(result.get(key) or "") for key in ("uid", "time", "sign", "client_type")
            }
            qrcode_image = str(result.get("qrcode") or "")
            if not qrcode_image.startswith("data:image/png;base64,"):
                raise RuntimeError("115未返回有效二维码图片")
            if not all(token_data.values()):
                raise RuntimeError("115未返回完整二维码登录参数")
            return {
                "provider": "115",
                "qrcode": qrcode_image,
                "token_data": token_data,
                "hint": "请使用 115 App 或支付宝扫一扫",
            }
        if provider == "quark":
            import qrcode

            from csx.vendor.drive.quark.client import QuarkClient

            result = QuarkClient.create_qrcode_login()
            token = str(result.get("qr_token") or "")
            qr_url = str(result.get("qr_url") or "")
            if not token or not qr_url:
                raise RuntimeError("夸克未返回完整二维码登录参数")
            image = qrcode.make(qr_url)
            output = BytesIO()
            image.save(output, format="PNG")
            return {
                "provider": "quark",
                "qrcode": "data:image/png;base64," + b64encode(output.getvalue()).decode("ascii"),
                "token_data": {"qr_token": token},
                "hint": "请使用夸克 App 扫描二维码",
            }
        raise ValueError(f"unsupported QR login provider: {provider}")

    @staticmethod
    def check_qrcode(provider: str, token_data: dict) -> dict:
        """Poll a provider QR session and expose only the normalized status/cookie."""
        provider = provider.strip().lower()
        if provider == "115":
            from csx.vendor.drive.p115.client import P115ClientManager

            result = P115ClientManager.check_qrcode_login(
                uid=str(token_data.get("uid") or ""),
                qrcode_time=str(token_data.get("time") or ""),
                sign=str(token_data.get("sign") or ""),
                client_type=str(token_data.get("client_type") or "alipaymini"),
            )
        elif provider == "quark":
            from csx.vendor.drive.quark.client import QuarkClient

            result = QuarkClient.check_qrcode_login(qr_token=str(token_data.get("qr_token") or ""))
        else:
            raise ValueError(f"unsupported QR login provider: {provider}")

        raw_status = str(result.get("status") or "waiting").lower()
        if raw_status == "cancelled":
            status = "expired"
        elif raw_status in {"waiting", "scanned", "success", "expired"}:
            status = raw_status
        else:
            status = "waiting"
        return {
            "status": status,
            "message": str(result.get("message") or "等待扫码"),
            "cookie": str(result["cookie"])
            if status == "success" and result.get("cookie")
            else None,
        }

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
