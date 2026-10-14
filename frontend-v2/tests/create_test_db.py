"""Create the SQLite schema for the isolated Playwright backend.

Called as part of the Playwright webServer command before uvicorn boots, so the
fresh e2e SQLite database has all tables (mirrors tests/conftest.py baseline).
Usage:
    python tests/create_test_db.py <sqlite-path>
"""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine

from app.db.base import Base

# Importing app.main registers all ORM models on Base.metadata, so create_all
# below creates every table (mirrors tests/conftest.py).
from app.main import app  # noqa: F401,E402

os.environ.setdefault("ARIA_SCHEDULER_ENABLED", "false")


def reset_test_database(path: str, *, workspace: Path | None = None) -> Path:
    """Reset only an explicitly named E2E database inside the workspace.

    create_all cannot upgrade an old schema. This runner owns disposable E2E
    databases, never the normal app database. Validate every deletion target
    before removing the database and its SQLite sidecars.
    """
    root = (workspace or Path(__file__).resolve().parents[2]).resolve()
    requested = Path(path)
    target = (requested if requested.is_absolute() else root / requested).resolve()
    if not target.is_relative_to(root) or not target.name.startswith("e2e-") or target.suffix != ".db":
        raise ValueError("Use a disposable e2e-*.db file inside the workspace")
    files = [target, *(target.with_name(target.name + suffix) for suffix in ("-wal", "-shm", "-journal"))]
    if any(not item.resolve().is_relative_to(root) or item.is_symlink() for item in files):
        raise ValueError("Refusing a database or sidecar outside the workspace")
    for item in files:
        item.unlink(missing_ok=True)
    engine = create_engine(f"sqlite:///{target.as_posix()}", connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    return target


def main() -> None:
    target = reset_test_database(sys.argv[1] if len(sys.argv) > 1 else "e2e-smoke-v2.db")
    print(f"Reset current E2E schema: {target.name}")


if __name__ == "__main__":
    main()
