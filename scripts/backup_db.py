"""Create a timestamped pg_dump backup from DATABASE_URL.

Usage:
    python scripts/backup_db.py [--out DIR]

Defaults to the BACKUP_DIR env or ./backups. Prunes backups older than
--keep (default 14) to bound disk usage. Delegates to app.services.backup;
the scheduler runs the same routine daily when ARIA_BACKUP_ENABLED=true.
"""

import argparse
import os
import sys
from pathlib import Path

# Make the script runnable from the repo root without PYTHONPATH=backend.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=os.environ.get("BACKUP_DIR", "backups"))
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url or url.startswith("sqlite"):
        print("DATABASE_URL must point at a PostgreSQL database", file=sys.stderr)
        return 2

    from app.services.backup import create_backup

    try:
        destination = create_backup(
            database_url=url, out_dir=args.out, keep=args.keep
        )
    except Exception as exc:
        print(f"backup failed: {exc}", file=sys.stderr)
        return 1
    print(f"backup written to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
