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
        # 针对每个 provider，优先选取 is_enabled=True 且 is_primary=True 的账号
        accounts = (
            db.query(Account)
            .filter(Account.is_enabled.is_(True))
            .order_by(Account.is_primary.desc(), Account.id.asc())
            .all()
        )
        res = {}
        for acc in accounts:
            if acc.provider in {"115", "quark"} and acc.provider not in res:
                res[acc.provider] = cls.build(acc.provider, decrypt_credential(acc.credential))
        return res

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
            return QuarkClient.run_checkin(credential, checkin_url)
        raise ValueError(f"check-in unsupported for {provider}")

    @staticmethod
    def get_account_profile(provider: str, credential: str) -> dict:
        """Fetch account capacity, nickname, avatar, and VIP info matching CS AccountInfo component."""
        provider = provider.lower()
        if provider == "115":
            try:
                from csx.vendor.drive.p115.client import P115ClientManager

                mgr = P115ClientManager(credential)
                user_res = mgr._rate_limited_call(mgr.client.user_my_info)
                user_data = (user_res or {}).get("data") or {}
                vip_data = user_data.get("vip") or {}
                face_data = user_data.get("face") or {}
                space_res = mgr._rate_limited_call(mgr.client.fs_index_info, payload=0)
                space_data = ((space_res or {}).get("data") or {}).get("space_info") or {}
                is_forever = bool(vip_data.get("is_forever"))
                is_vip = bool(vip_data.get("is_vip")) or is_forever
                return {
                    "connected": True,
                    "user_name": str(user_data.get("uname") or "未知用户"),
                    "avatar": str(face_data.get("face_s") or ""),
                    "is_vip": is_vip,
                    "is_forever_vip": is_forever,
                    "vip_expire": "永久" if is_forever else str(vip_data.get("expire_str") or ""),
                    "total_space": str(
                        (space_data.get("all_total") or {}).get("size_format") or ""
                    ),
                    "used_space": str((space_data.get("all_use") or {}).get("size_format") or ""),
                    "remaining_space": str(
                        (space_data.get("all_remain") or {}).get("size_format") or ""
                    ),
                }
            except Exception as e:
                return {"connected": False, "error": str(e)}
        if provider == "quark":
            try:
                from csx.vendor.drive.quark.client import QuarkClient

                qc = QuarkClient(cookie=credential)
                res = qc.get_account_info() or {}
                user = res.get("user") or {}
                storage = res.get("storage") or {}
                return {
                    "connected": res.get("connected", True),
                    "user_name": str(user.get("name") or "夸克用户"),
                    "avatar": str(user.get("avatar") or ""),
                    "is_vip": user.get("is_vip", False),
                    "vip_expire": str(user.get("vip_expire_date") or ""),
                    "total_space": str(storage.get("total") or ""),
                    "used_space": str(storage.get("used") or ""),
                    "remaining_space": str(storage.get("remaining") or ""),
                }
            except Exception as e:
                return {"connected": False, "error": str(e)}
        return {}
