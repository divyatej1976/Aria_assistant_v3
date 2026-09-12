"""Scheduled PostgreSQL backups (pg_dump) with retention pruning.

The scheduler job runs under an advisory lock like every other background
job, so multi-replica deployments produce one backup per interval. The CLI
in scripts/backup_db.py delegates to `create_backup` here.
"""

import gzip
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import make_url


class BackupError(RuntimeError):
    pass


def pg_env(url: str) -> dict[str, str]:
    parsed = make_url(url)
    return {
        **os.environ,
        "PGHOST": parsed.host or "localhost",
        "PGPORT": str(parsed.port or 5432),
        "PGUSER": parsed.username or "",
        "PGPASSWORD": parsed.password or "",
        "PGDATABASE": parsed.database or "",
    }


def create_backup(
    *,
    database_url: str,
    out_dir: Path | str,
    keep: int = 14,
    pg_dump: str | None = None,
    runner=None,
) -> Path:
    """Dump `database_url` to a timestamped gzip archive; prune older backups.

    `runner` injects a fake subprocess for tests; defaults to subprocess.run
    with the pg_dump binary. Raises BackupError on dump failure.
    """
    if not database_url or database_url.startswith("sqlite"):
        raise BackupError("Backups require a PostgreSQL DATABASE_URL")
    env = pg_env(database_url)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = out / f"aria-{stamp}.dump.gz"
    binary = pg_dump or os.environ.get("PG_DUMP", "pg_dump")

    if runner is None:

        def runner(cmd, *, env, check, stdout):  # noqa: ANN001 - subprocess signature
            # Stream pg_dump stdout THROUGH the gzip layer. Passing the
            # GzipFile directly as subprocess' stdout would let the child
            # write to the underlying fd via fileno(), bypassing compression
            # and producing a plaintext dump with a .dump.gz name (caught in
            # the production drill).
            proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE)
            try:
                shutil.copyfileobj(proc.stdout, stdout)
            finally:
                proc.stdout.close()
                returncode = proc.wait()
            if check and returncode != 0:
                raise subprocess.CalledProcessError(returncode, cmd)

    with gzip.GzipFile(str(destination), mode="wb") as handle:
        try:
            # No `-f -`: implicit stdout is equivalent, and `-f -` breaks under
            # `docker exec` wrappers (0-byte stream observed on Docker Desktop
            # for Windows) where PG_DUMP indirection is common.
            runner([binary, "-Fc", "--no-owner"], env=env, check=True, stdout=handle)
        except Exception as exc:
            raise BackupError(f"pg_dump failed: {exc}") from exc

    backups = sorted(out.glob("aria-*.dump.gz"), reverse=True)
    for stale in backups[max(0, keep):]:
        stale.unlink()
    return destination


def latest_backup(out_dir: Path | str) -> Path | None:
    candidates = sorted(Path(out_dir).glob("aria-*.dump.gz"), reverse=True)
    return candidates[0] if candidates else None


def run_backup_job() -> bool:
    """Scheduler entry point: one backup when enabled. Returns True when one ran."""
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.aria_backup_enabled:
        return False
    from app.core.config import get_settings as _s

    database_url = _s().database_url
    destination = create_backup(
        database_url=database_url,
        out_dir=settings.aria_backup_dir,
        keep=settings.aria_backup_keep,
    )
    print(f"backup written to {destination}")
    return True
