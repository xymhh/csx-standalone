import os

import pytest

from csx.adapters.drive.registry import DriveRegistry


@pytest.mark.net
def test_configured_real_drive_share_smoke():
    provider = os.getenv("CSX_SMOKE_PROVIDER", "quark")
    share_url = os.getenv("CSX_SMOKE_SHARE_URL", "")
    drives = DriveRegistry.from_environment()
    if not share_url or provider not in drives:
        pytest.skip("configure CSX_SMOKE_PROVIDER, CSX_SMOKE_SHARE_URL and provider cookie")
    assert drives[provider].check_share(share_url).valid
