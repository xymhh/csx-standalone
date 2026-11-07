"""测试隔离：独立数据目录 + 固定管理员口令。必须在 import csx 之前设置环境变量。"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="csx-test-"))
os.environ.setdefault("CSX_DATA_DIR", str(_TMP))
os.environ.setdefault("CSX_ADMIN_USER", "admin")
os.environ.setdefault("CSX_ADMIN_PASSWORD", "test-password-123")

PASSWORD = os.environ["CSX_ADMIN_PASSWORD"]


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from csx.api.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    from csx.infra import ratelimit

    ratelimit._attempts.clear()
    yield
    ratelimit._attempts.clear()
