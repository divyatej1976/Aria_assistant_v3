"""Create a timestamped pg_dump backup from DATABASE_URL.

Usage:
    python scripts/backup_db.py [--out DIR]

Defaults to the BACKUP_DIR env or ./backups. Prunes backups older than
--keep (default 14) to bound disk usage.
"""

import argparse
import datetime
import gzip
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy.engine import make_url


def _pg_env(url) -> dict[str, str]:
    parsed = make_url(url)
    return {
        **os.environ,
        "PGHOST": parsed.host or "localhost",
        "PGPORT": str(parsed.port or 5432),
        "PGUSER": parsed.username or "",
        "PGPASSWORD": parsed.password or "",
        "PGDATABASE": parsed.database or "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=os.environ.get("BACKUP_DIR", "backups"))
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url or url.startswith("sqlite"):
        print("DATABASE_URL must point at a PostgreSQL database", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = out_dir / f"aria-{stamp}.dump.gz"

    env = _pg_env(url)
    pg_dump = os.environ.get("PG_DUMP", "pg_dump")
    with gzip.GzipFile(str(destination), mode="wb") as handle:
        subprocess.run(
            [pg_dump, "-Fc", "--no-owner", "-f", "-"],
            env=env,
            check=True,
            stdout=handle,
        )
    print(f"backup written to {destination}")

    backups = sorted(out_dir.glob("aria-*.dump.gz"), reverse=True)
    for stale in backups[args.keep :]:
        stale.unlink()
        print(f"pruned {stale}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
