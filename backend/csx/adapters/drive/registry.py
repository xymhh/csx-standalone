"""Construct the supported vendor drives using environment credentials."""

from __future__ import annotations

import os


class DriveRegistry:
    @staticmethod
    def from_environment() -> dict[str, object]:
        from csx.vendor.core.cloud import CloudDriveCapability
        from csx.vendor.drive.p115.client import P115ClientManager
        from csx.vendor.drive.p115.provider import create_p115_provider
        from csx.vendor.drive.quark.client import QuarkClient
        from csx.vendor.drive.quark.provider import QuarkDrive, create_quark_provider

        result = {}
        cookie = os.getenv("CSX_115_COOKIE", "").strip()
        if cookie:
            manager = P115ClientManager(cookie)
            provider = create_p115_provider(manager)
            from .p115 import P115DriveAdapter

            result["115"] = P115DriveAdapter(
                provider.services[CloudDriveCapability.SHARE_TRANSFER],
                provider.services[CloudDriveCapability.FILE_QUERY],
            )
        quark_cookie = os.getenv("CSX_QUARK_COOKIE", "").strip()
        if quark_cookie:
            client = QuarkClient(cookie=quark_cookie)
            drive = QuarkDrive(client)
            provider = create_quark_provider(drive)
            from .quark import QuarkDriveAdapter

            result["quark"] = QuarkDriveAdapter(
                provider.services[CloudDriveCapability.SHARE_TRANSFER],
                provider.services[CloudDriveCapability.FILE_QUERY],
            )
        return result
