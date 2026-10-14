"""Scheduled PostgreSQL backups (pg_dump) with retention pruning.

The scheduler job runs under an advisory lock like every other background
job, so multi-replica deployments produce one backup per interval. The CLI
in scripts/backup_db.py delegates to `create_backup` here.
"""

import gzip
import os
import shutil
import subprocess
import tempfile
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
    encryption_key: str | None = None,
) -> Path:
    """Dump `database_url` to a timestamped gzip archive; prune older backups.

    `runner` injects a fake subprocess for tests; defaults to subprocess.run
    with the pg_dump binary. Raises BackupError on dump failure.

    When `encryption_key` (Fernet) is set, the archive is encrypted to
    `aria-<stamp>.dump.gz.enc` and the plaintext is removed, so PII never
    rests unencrypted; restore requires the same key.
    """
    if not database_url or database_url.startswith("sqlite"):
        raise BackupError("Backups require a PostgreSQL DATABASE_URL")
    env = pg_env(database_url)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = out / f"aria-{stamp}.dump.gz"
    binary = pg_dump or os.environ.get("PG_DUMP", "pg_dump")

    if runner is None:

        def runner(cmd, *, env, check, stdout):  # noqa: ANN001 - subprocess signature
            # Stream pg_dump stdout THROUGH the gzip layer. Passing the
            # GzipFile directly as subprocess' stdout would let the child
            # write to the underlying fd via fileno(), bypassing compression
            # and producing a plaintext dump with a .dump.gz name (caught in
            # the production drill).
            proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                shutil.copyfileobj(proc.stdout, stdout)
            finally:
                proc.stdout.close()
                returncode = proc.wait()
            if check and returncode != 0:
                raise subprocess.CalledProcessError(returncode, cmd)

    fd, temporary = tempfile.mkstemp(prefix=".aria-", suffix=".partial", dir=out)
    os.close(fd)
    staged = Path(temporary)
    encrypted_stage = staged.with_name(staged.name + ".enc")
    try:
        with gzip.GzipFile(str(staged), mode="wb") as handle:
            # No `-f -`: implicit stdout is equivalent, and `-f -` breaks under
            # `docker exec` wrappers (0-byte stream observed on Docker Desktop
            # for Windows) where PG_DUMP indirection is common.
            runner([binary, "-Fc", "--no-owner"], env=env, check=True, stdout=handle)
        if encryption_key:
            staged = _encrypt_backup(staged, encryption_key=encryption_key)
            destination = destination.with_name(destination.name + ".enc")
        staged.replace(destination)
    except Exception as exc:
        raise BackupError(f"backup failed (error_type={type(exc).__name__})") from None
    finally:
        Path(temporary).unlink(missing_ok=True)
        encrypted_stage.unlink(missing_ok=True)
    _prune_backups(out, keep=keep)
    return destination


def _prune_backups(out: Path, *, keep: int) -> None:
    backups = completed_backups(out)
    for stale in backups[max(0, keep):]:
        stale.unlink()


def _encrypt_backup(destination: Path, *, encryption_key: str) -> Path:
    """Fernet-encrypt a finished archive; remove the plaintext original."""
    from cryptography.fernet import Fernet, InvalidToken

    try:
        fernet = Fernet(encryption_key.encode("utf-8"))
    except Exception as exc:
        raise BackupError("invalid backup encryption key") from exc
    try:
        token = fernet.encrypt(destination.read_bytes())
    except InvalidToken as exc:
        raise BackupError("backup encryption failed") from exc
    encrypted = destination.with_name(destination.name + ".enc")
    fd = os.open(encrypted, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(token)
    destination.unlink()
    return encrypted


def decrypt_backup(data: bytes, *, encryption_key: str) -> bytes:
    """Decrypt an `.enc` archive; raises BackupError on wrong key/corruption."""
    from cryptography.fernet import Fernet, InvalidToken

    try:
        return Fernet(encryption_key.encode("utf-8")).decrypt(data)
    except InvalidToken as exc:
        raise BackupError("backup decryption failed (wrong key or corrupt file)") from exc
    except Exception as exc:
        raise BackupError("invalid backup encryption key") from exc


def completed_backups(out_dir: Path | str) -> list[Path]:
    """Discover only published plaintext/encrypted files, never partial stages."""
    return sorted((path for path in Path(out_dir).glob("aria-*.dump.gz*")
                   if path.is_file() and path.name.endswith((".dump.gz", ".dump.gz.enc"))), reverse=True)


def latest_backup(out_dir: Path | str) -> Path | None:
    candidates = completed_backups(out_dir)
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
        encryption_key=settings.aria_backup_encryption_key,
    )
    print(f"backup written to {destination}")
    return True
