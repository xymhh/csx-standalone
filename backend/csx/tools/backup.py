"""Create a compressed online SQLite backup: ``python -m csx.tools.backup``."""

from __future__ import annotations

import json

from csx.infra.backup import create_backup
from csx.infra.db import engine
from csx.infra.settings import settings


def main() -> None:
    result = create_backup(engine, settings.data_dir / "backups")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
