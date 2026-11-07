from __future__ import annotations

import subprocess
import sys


def test_domain_imports_do_not_load_frameworks() -> None:
    script = (
        "import sys; "
        "import csx.domain.media, csx.domain.subscription, csx.domain.resource, csx.domain.task; "
        "assert not {'sqlalchemy', 'fastapi', 'pydantic'} & sys.modules.keys()"
    )
    subprocess.run([sys.executable, "-c", script], check=True)
