"""Phase 12.9 DR scripts: DATABASE_URL parsing for pg_dump/pg_restore."""

from scripts.backup_db import main as _backup_cli  # noqa: F401 - CLI delegates to the service
from scripts.restore_db import _pg_env as restore_env

from app.services.backup import pg_env as backup_env


def test_backup_pg_env_parses_url() -> None:
    env = backup_env("postgresql+psycopg://aria:pass@db.example.com:5433/aria")
    assert env["PGHOST"] == "db.example.com"
    assert env["PGPORT"] == "5433"
    assert env["PGUSER"] == "aria"
    assert env["PGPASSWORD"] == "pass"
    assert env["PGDATABASE"] == "aria"


def test_restore_pg_env_uses_defaults() -> None:
    env = restore_env("postgresql+psycopg://aria@localhost/other")
    assert env["PGHOST"] == "localhost"
    assert env["PGPORT"] == "5432"
    assert env["PGUSER"] == "aria"
    assert env["PGDATABASE"] == "other"
