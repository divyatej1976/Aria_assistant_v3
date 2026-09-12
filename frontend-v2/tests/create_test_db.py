"""Create the SQLite schema for the isolated Playwright backend.

Called as part of the Playwright webServer command before uvicorn boots, so the
fresh e2e SQLite database has all tables (mirrors tests/conftest.py baseline).
Usage:
    python tests/create_test_db.py <sqlite-path>
"""

import os
import sys

from sqlalchemy import create_engine

from app.db.base import Base

# Importing app.main registers all ORM models on Base.metadata, so create_all
# below creates every table (mirrors tests/conftest.py).
from app.main import app  # noqa: F401,E402

os.environ.setdefault("ARIA_SCHEDULER_ENABLED", "false")


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "./e2e-smoke-v2.db"
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    print(f"created schema at {path}")


if __name__ == "__main__":
    main()
