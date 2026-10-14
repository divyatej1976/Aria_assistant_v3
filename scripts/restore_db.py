"""Restore a pg_dump custom-format backup into the DATABASE_URL target.

Usage:
    python scripts/restore_db.py [FILE]

Defaults to the most recent backup in BACKUP_DIR (./backups). Encrypted
archives (aria-*.dump.gz.enc) are decrypted with ARIA_BACKUP_ENCRYPTION_KEY
before restore.
"""

import argparse
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
    parser.add_argument("file", nargs="?", help="backup file (.dump.gz)")
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url or url.startswith("sqlite"):
        print("DATABASE_URL must point at a PostgreSQL database", file=sys.stderr)
        return 2

    backup_dir = Path(os.environ.get("BACKUP_DIR", "backups"))
    if args.file:
        source = Path(args.file)
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
        from app.services.backup import completed_backups

        candidates = completed_backups(backup_dir)
        if not candidates:
            print("no backups found", file=sys.stderr)
            return 2
        source = candidates[0]

    data = source.read_bytes()
    if source.suffix == ".enc":
        key = os.environ.get("ARIA_BACKUP_ENCRYPTION_KEY", "")
        if not key:
            print("ARIA_BACKUP_ENCRYPTION_KEY is required for encrypted backups",
                  file=sys.stderr)
            return 2
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
        from app.services.backup import decrypt_backup

        try:
            data = decrypt_backup(data, encryption_key=key)
        except Exception as exc:
            print(f"decrypt failed (error_type={type(exc).__name__})", file=sys.stderr)
            return 1

    data = gzip.decompress(data)

    env = _pg_env(url)
    pg_restore = os.environ.get("PG_RESTORE", "pg_restore")
    try:
        subprocess.run(
            [pg_restore, "--clean", "--if-exists", "--no-owner", "-d", env["PGDATABASE"]],
            env=env, check=True, input=data, stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"restore failed (error_type={type(exc).__name__})", file=sys.stderr)
        return 1
    print(f"restored from {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
