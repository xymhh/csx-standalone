"""Restore a compressed backup: ``python -m csx.tools.restore <file>``."""

from __future__ import annotations

import argparse
import json

from csx.infra.backup import restore_backup
from csx.infra.db import engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely restore a CloudSubscribeX backup")
    parser.add_argument("backup_file", help="Path to csx-backup-*.db.gz")
    arguments = parser.parse_args()
    result = restore_backup(engine, arguments.backup_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
