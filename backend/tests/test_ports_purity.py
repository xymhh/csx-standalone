from __future__ import annotations

import subprocess
import sys


def test_domain_imports_do_not_load_frameworks_or_vendor():
    code = """import sys, csx.domain.media, csx.domain.naming, csx.domain.resource, csx.domain.task
bad = {'sqlalchemy', 'fastapi', 'pydantic', 'csx.vendor'}
assert not [name for name in sys.modules if any(name == item or name.startswith(item + '.') for item in bad)]
"""
    subprocess.run([sys.executable, "-c", code], check=True)
