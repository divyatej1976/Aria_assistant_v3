"""Phase 12.9 DR scripts: DATABASE_URL parsing for pg_dump/pg_restore."""

from scripts.backup_db import main as _backup_cli  # noqa: F401 - CLI delegates to the service
from scripts.restore_db import _pg_env as restore_env

from app.services.backup import BackupError, create_backup, decrypt_backup
from app.services.backup import pg_env as backup_env


def test_backup_failure_does_not_expose_runner_details(tmp_path):
    import pytest

    def fail(*args, **kwargs):
        raise RuntimeError("private database password and learner data")

    with pytest.raises(BackupError) as error:
        create_backup(database_url="postgresql://aria:pw@localhost/aria",
                      out_dir=tmp_path, runner=fail)
    assert str(error.value) == "backup failed (error_type=RuntimeError)"


def test_backup_cli_does_not_print_untrusted_exception(monkeypatch, capsys, tmp_path):
    import sys

    def fail(**kwargs):
        raise RuntimeError("private database password and learner data")

    monkeypatch.setenv("DATABASE_URL", "postgresql://aria:pw@localhost/aria")
    monkeypatch.setattr(sys, "argv", ["backup_db.py", "--out", str(tmp_path)])
    monkeypatch.setattr("app.services.backup.create_backup", fail)
    assert _backup_cli() == 1
    output = capsys.readouterr().err
    assert "error_type=RuntimeError" in output
    assert "private database" not in output


def test_backup_cli_honors_configured_encryption(monkeypatch, capsys, tmp_path):
    import sys

    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    monkeypatch.setenv("DATABASE_URL", "postgresql://aria:pw@localhost/aria")
    monkeypatch.setenv("ARIA_BACKUP_ENCRYPTION_KEY", key)
    monkeypatch.setattr(sys, "argv", ["backup_db.py", "--out", str(tmp_path)])

    def create(**kwargs):
        return create_backup(**kwargs, runner=_fake_runner(b"private dump"))

    monkeypatch.setattr("app.services.backup.create_backup", create)
    assert _backup_cli() == 0
    assert not list(tmp_path.glob("*.gz"))
    archives = list(tmp_path.glob("*.enc"))
    assert len(archives) == 1
    import gzip

    assert gzip.decompress(decrypt_backup(archives[0].read_bytes(), encryption_key=key)) == b"private dump"
    assert key not in capsys.readouterr().out


def test_restore_decrypt_failure_does_not_print_untrusted_exception(monkeypatch, capsys, tmp_path):
    import sys

    from scripts.restore_db import main

    source = tmp_path / "backup.dump.gz.enc"
    source.write_bytes(b"encrypted")

    def fail(*args, **kwargs):
        raise RuntimeError("private encryption key and learner data")

    monkeypatch.setenv("DATABASE_URL", "postgresql://aria:pw@localhost/aria")
    monkeypatch.setenv("ARIA_BACKUP_ENCRYPTION_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", ["restore_db.py", str(source)])
    monkeypatch.setattr("app.services.backup.decrypt_backup", fail)
    assert main() == 1
    output = capsys.readouterr().err
    assert "error_type=RuntimeError" in output
    assert "private encryption" not in output


def test_restore_subprocess_failure_is_sanitized(monkeypatch, capsys, tmp_path):
    import gzip
    import subprocess
    import sys

    from scripts.restore_db import main

    source = tmp_path / "backup.dump.gz"
    source.write_bytes(gzip.compress(b"dump"))
    monkeypatch.setenv("DATABASE_URL", "postgresql://aria:pw@localhost/aria")
    monkeypatch.setattr(sys, "argv", ["restore_db.py", str(source)])

    def fail(cmd, **kwargs):
        assert kwargs["stderr"] == subprocess.DEVNULL
        raise subprocess.CalledProcessError(1, cmd, stderr=b"private learner data")

    monkeypatch.setattr(subprocess, "run", fail)
    assert main() == 1
    output = capsys.readouterr().err
    assert "error_type=CalledProcessError" in output
    assert "private learner" not in output


def test_backup_subprocess_stderr_and_traceback_are_private(monkeypatch, tmp_path):
    import io
    import subprocess
    import traceback

    import pytest

    class Process:
        stdout = io.BytesIO(b"partial dump")

        def wait(self):
            return 1

    def launch(cmd, **kwargs):
        assert kwargs["stderr"] == subprocess.DEVNULL
        return Process()

    monkeypatch.setattr(subprocess, "Popen", launch)
    with pytest.raises(BackupError) as raised:
        create_backup(database_url="postgresql://aria:pw@localhost/aria", out_dir=tmp_path)
    assert raised.value.__suppress_context__ is True
    assert "CalledProcessError" in str(raised.value)
    rendered = "".join(traceback.format_exception(raised.value))
    assert "returned non-zero exit status" not in rendered


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


def _fake_runner(payload: bytes):
    def run(cmd, *, env, check, stdout):  # noqa: ANN001,ANN202 - subprocess signature
        stdout.write(payload)

    return run


def test_failed_dump_preserves_previous_backup_and_removes_partial(tmp_path):
    import pytest

    previous = create_backup(database_url="postgresql://aria:pw@localhost/aria", out_dir=tmp_path,
                             runner=_fake_runner(b"previous"))
    original = previous.read_bytes()

    def fail(cmd, **kwargs):
        kwargs["stdout"].write(b"partial private data")
        raise RuntimeError("dump failed")

    with pytest.raises(BackupError):
        create_backup(database_url="postgresql://aria:pw@localhost/aria", out_dir=tmp_path,
                      runner=fail, keep=1)
    assert list(tmp_path.iterdir()) == [previous]
    assert previous.read_bytes() == original


def test_encryption_failure_leaves_no_plaintext_archive(tmp_path):
    import pytest

    with pytest.raises(BackupError):
        create_backup(database_url="postgresql://aria:pw@localhost/aria", out_dir=tmp_path,
                      runner=_fake_runner(b"private dump"), encryption_key="invalid")
    assert list(tmp_path.iterdir()) == []


def test_backup_discovery_and_retention_ignore_incomplete_files(tmp_path):
    from app.services.backup import _prune_backups, completed_backups, latest_backup

    old = tmp_path / "aria-20000101T000000Z.dump.gz"
    newest = tmp_path / "aria-20000102T000000Z.dump.gz.enc"
    partial = tmp_path / "aria-99990101T000000Z.dump.gz.partial"
    directory = tmp_path / "aria-99990102T000000Z.dump.gz"
    for path in (old, newest, partial):
        path.write_bytes(b"test")
    directory.mkdir()
    assert completed_backups(tmp_path) == [newest, old]
    assert latest_backup(tmp_path) == newest
    _prune_backups(tmp_path, keep=1)
    assert not old.exists()
    assert newest.exists() and partial.exists() and directory.is_dir()


def test_encrypted_backup_round_trips(tmp_path) -> None:
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode("utf-8")
    destination = create_backup(
        database_url="postgresql+psycopg://aria:pw@localhost:5432/aria",
        out_dir=tmp_path,
        keep=14,
        runner=_fake_runner(b"PGDUMP-CUSTOM-FORMAT"),
        encryption_key=key,
    )
    assert destination.suffix == ".enc"
    assert destination.is_file()
    # Plaintext must not rest on disk.
    assert list(tmp_path.glob("aria-*.dump.gz")) == []
    import gzip as _gzip

    assert _gzip.decompress(
        decrypt_backup(destination.read_bytes(), encryption_key=key)
    ) == b"PGDUMP-CUSTOM-FORMAT"


def test_encrypted_backup_wrong_key_fails(tmp_path) -> None:
    import pytest
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode("utf-8")
    other = Fernet.generate_key().decode("utf-8")
    destination = create_backup(
        database_url="postgresql+psycopg://aria:pw@localhost:5432/aria",
        out_dir=tmp_path,
        keep=14,
        runner=_fake_runner(b"data"),
        encryption_key=key,
    )
    with pytest.raises(BackupError, match="decryption failed"):
        decrypt_backup(destination.read_bytes(), encryption_key=other)


def test_plaintext_backup_unchanged_without_key(tmp_path) -> None:
    import gzip as _gzip

    destination = create_backup(
        database_url="postgresql+psycopg://aria:pw@localhost:5432/aria",
        out_dir=tmp_path,
        keep=14,
        runner=_fake_runner(b"data"),
    )
    assert destination.suffix == ".gz"
    assert _gzip.decompress(destination.read_bytes()) == b"data"
