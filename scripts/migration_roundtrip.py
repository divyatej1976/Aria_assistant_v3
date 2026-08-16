"""Verify the alembic migration chain applies and rolls back cleanly.

Runs `upgrade head` -> `downgrade base` -> `upgrade head` against a disposable
database. Requires DATABASE_URL to point at a real (non-SQLite) database.
Used by CI's Postgres job and locally to confirm migrations 0001-0014.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> None:
    env = {**os.environ, "DATABASE_URL": os.environ["DATABASE_URL"]}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)


def main() -> None:
    url = os.environ.get("DATABASE_URL", "")
    if not url or url.startswith("sqlite"):
        raise SystemExit("DATABASE_URL must point at a disposable PostgreSQL database")
    run("upgrade", "head")
    run("downgrade", "base")
    run("upgrade", "head")
    print("Migration round-trip OK: upgrade head -> downgrade base -> upgrade head")


if __name__ == "__main__":
    main()
