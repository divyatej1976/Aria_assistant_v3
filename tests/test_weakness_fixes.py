"""Weakness-fix acceptance: durable audio listing, shared rate limiting,
scheduled backups, and proxy/compose deployment artifacts."""

import gzip
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-9", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class _FakeTTS:
    def generate(self, *, text: str) -> tuple[bytes, str, int]:
        return b"AUDIO", "audio/mpeg", 10


# --- Durable audio listing ---

def test_audio_list_endpoint_durable_and_scoped(client: TestClient, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: _FakeTTS())
    from app.services.audio_storage import LocalAudioStorage

    monkeypatch.setattr(
        "app.services.audio.get_audio_storage",
        lambda: LocalAudioStorage(tmp_path / "audiofiles"),
    )
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"list-{tag}@example.com")
    auth = _headers(user["access_token"])
    other = _register(client, f"list-other-{tag}@example.com")

    ctx = client.post("/api/v1/contexts", headers=auth, json={"title": "Ctx A"}).json()["id"]
    ctx2 = client.post("/api/v1/contexts", headers=auth, json={"title": "Ctx B"}).json()["id"]
    note = client.post(
        "/api/v1/notes", headers=auth, json={"context_id": ctx, "title": "N", "body": "Body."}
    ).json()
    res = client.post(
        "/api/v1/resources/text",
        headers=auth,
        json={"context_id": ctx2, "title": "R", "text": "Resource body text here."},
    ).json()
    note_art = client.post(f"/api/v1/audio/notes/{note['id']}/generate", headers=auth).json()
    res_art = client.post(f"/api/v1/audio/resources/{res['id']}/generate", headers=auth).json()

    # Durable listing per context — no localStorage involved.
    listed_a = client.get(f"/api/v1/audio?context_id={ctx}", headers=auth).json()
    listed_b = client.get(f"/api/v1/audio?context_id={ctx2}", headers=auth).json()
    assert [item["id"] for item in listed_a] == [note_art["id"]]
    assert [item["id"] for item in listed_b] == [res_art["id"]]
    assert listed_a[0]["title"] == "N"
    assert listed_b[0]["title"] == "R"
    assert listed_a[0]["source_type"] == "NOTE"
    assert listed_a[0]["status"] == "READY"
    assert {"id", "source_id", "title", "status", "position_seconds", "completed",
            "duration_seconds", "created_at", "content_type", "source_type"} <= set(listed_a[0])

    # All owned artifacts, newest first, without filter.
    everything = client.get("/api/v1/audio", headers=auth).json()
    assert {item["id"] for item in everything} == {note_art["id"], res_art["id"]}

    # Owner isolation: other learner sees nothing.
    assert client.get("/api/v1/audio", headers=_headers(other["access_token"])).json() == []

    # Delete is reflected in the durable list.
    client.delete(f"/api/v1/audio/{note_art['id']}", headers=auth)
    after = client.get(f"/api/v1/audio?context_id={ctx}", headers=auth).json()
    assert after == []


def test_audio_list_progress_roundtrip(client: TestClient, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: _FakeTTS())
    from app.services.audio_storage import LocalAudioStorage

    monkeypatch.setattr(
        "app.services.audio.get_audio_storage",
        lambda: LocalAudioStorage(tmp_path / "audiofiles"),
    )
    tag = uuid.uuid4().hex[:8]
    user = _register(client, f"list-prog-{tag}@example.com")
    auth = _headers(user["access_token"])
    ctx = client.post("/api/v1/contexts", headers=auth, json={"title": "Ctx"}).json()["id"]
    note = client.post(
        "/api/v1/notes", headers=auth, json={"context_id": ctx, "title": "N", "body": "B."}
    ).json()
    art = client.post(f"/api/v1/audio/notes/{note['id']}/generate", headers=auth).json()
    client.put(
        f"/api/v1/audio/{art['id']}/progress", headers=auth,
        json={"position_seconds": 7, "completed": True},
    )
    listed = client.get(f"/api/v1/audio?context_id={ctx}", headers=auth).json()
    assert listed[0]["position_seconds"] == 7
    assert listed[0]["completed"] is True


# --- Shared (DB-backed) rate limiting ---

def test_db_rate_limiter_shared_and_enforced(session_factory) -> None:
    from app.security.rate_limit import allow_request_db

    factory = session_factory
    key = f"test:{uuid.uuid4()}"
    assert allow_request_db(key, limit=2, window_seconds=60, session_factory=factory)
    assert allow_request_db(key, limit=2, window_seconds=60, session_factory=factory)
    # Third request inside the window is rejected — shared state, one factory.
    assert not allow_request_db(key, limit=2, window_seconds=60, session_factory=factory)
    # Distinct key unaffected.
    assert allow_request_db(f"test:{uuid.uuid4()}", limit=2, window_seconds=60,
                            session_factory=factory)


def test_db_rate_limiter_window_resets(session_factory) -> None:

    from sqlalchemy import select

    from app.db.models import RateLimitBucket
    from app.security.rate_limit import allow_request_db

    factory = session_factory
    key = f"test-reset:{uuid.uuid4()}"
    assert allow_request_db(key, limit=1, window_seconds=60, session_factory=factory)
    assert not allow_request_db(key, limit=1, window_seconds=60, session_factory=factory)
    # Age the window beyond the limit: next call starts a fresh window.
    db = factory()
    try:
        row = db.scalar(select(RateLimitBucket).where(RateLimitBucket.key == key))
        row.window_started_at = datetime.now(UTC) - timedelta(seconds=120)
        db.commit()
    finally:
        db.close()
    assert allow_request_db(key, limit=1, window_seconds=60, session_factory=factory)


def test_db_rate_limiter_fails_open_on_infra_error() -> None:
    from app.security.rate_limit import allow_request_db

    def _boom():
        raise RuntimeError("db down")

    assert allow_request_db(f"k:{uuid.uuid4()}", limit=1, window_seconds=60,
                            session_factory=_boom) is True


# --- Scheduled backups ---

def test_create_backup_runs_and_prunes(tmp_path: Path) -> None:
    from app.services.backup import create_backup, latest_backup

    out = tmp_path / "backups"

    def _fake_runner(cmd, *, env, check, stdout):
        assert cmd[0].endswith("pg_dump") or cmd[0] == "pg_dump"
        assert "--no-owner" in cmd and "-Fc" in cmd
        stdout.write(b"PGDMP-fake")  # stdout is the open GzipFile handle

    destination = create_backup(
        database_url="postgresql+psycopg://u:p@db:5432/aria",
        out_dir=out,
        keep=2,
        runner=_fake_runner,
    )
    assert destination.exists()
    with gzip.open(destination, "rb") as handle:
        assert handle.read() == b"PGDMP-fake"
    # Seed older backups and verify pruning keeps only the newest 2.
    for stamp in ("20000101T000000Z", "20000102T000000Z", "20000103T000000Z"):
        (out / f"aria-{stamp}.dump.gz").write_bytes(b"old")
    create_backup(
        database_url="postgresql+psycopg://u:p@db:5432/aria",
        out_dir=out,
        keep=2,
        runner=_fake_runner,
    )
    backups = sorted(out.glob("aria-*.dump.gz"), reverse=True)
    assert len(backups) == 2
    assert latest_backup(out) == backups[0]


def _pg_dump_stub(directory: Path) -> tuple[Path, bytes]:
    """Cross-platform fake pg_dump emitting custom-format-like bytes.

    Stub output starts with "PGDMP" (the real pg_dump custom-format magic),
    so any test reading the raw .dump.gz can tell plaintext from gzip.
    """
    import sys

    text = "PGDMP-ARIA-BACKUP-REGRESSION"
    if sys.platform == "win32":
        stub = directory / "pg_dump.cmd"
        stub.write_text(f"@echo off\r\necho {text}\r\n", encoding="utf-8")
        payload = text.encode() + b"\r\n"
    else:
        stub = directory / "pg_dump_stub.sh"
        stub.write_text(f"#!/bin/sh\nprintf '{text}'\n", encoding="utf-8")
        stub.chmod(0o755)
        payload = text.encode()
    return stub, payload


def _assert_real_gzip_wrapped_dump(destination: Path, payload: bytes) -> None:
    """Verify the backup is a real gzip archive of the exact pg_dump bytes.

    Guards the fd-bypass regression: handing the GzipFile to the child as
    stdout lets it write plaintext via fileno(), bypassing the compression
    layer and producing a plaintext file named .dump.gz (caught live in the
    production DR drill).
    """
    raw = destination.read_bytes()
    assert raw[:2] == b"\x1f\x8b", "backup is not gzip-wrapped (fd bypass or truncation)"
    body = gzip.decompress(raw)
    assert body == payload, "decompressed dump is not exactly the pg_dump output"
    assert body.startswith(b"PGDMP"), "dump lacks the pg_dump custom-format signature"


def test_create_backup_default_runner_gzip_wraps_output(tmp_path: Path) -> None:
    """The production path (runner=None) must stream pg_dump stdout THROUGH
    the gzip layer; the .dump.gz must never contain plaintext dump bytes."""
    from app.services.backup import create_backup

    stub, payload = _pg_dump_stub(tmp_path)
    destination = create_backup(
        database_url="postgresql+psycopg://aria:pw@db:5432/aria",
        out_dir=tmp_path / "backups",
        pg_dump=str(stub),
        keep=1,
    )
    _assert_real_gzip_wrapped_dump(destination, payload)


def test_gzip_fd_bypass_is_caught_by_backup_verification(tmp_path: Path) -> None:
    """Negative control: replay the historical bug (child inherits the
    GzipFile fd and writes plaintext straight into the file) and prove the
    verification rejects it instead of passing a corrupt backup."""
    import subprocess

    import pytest

    from app.services.backup import pg_env

    stub, payload = _pg_dump_stub(tmp_path)
    destination = tmp_path / "aria-bypass.dump.gz"
    with gzip.GzipFile(str(destination), mode="wb") as handle:
        # The buggy wiring: stdout handed the GzipFile itself, so the child
        # writes to the underlying fd, bypassing the compression stream.
        proc = subprocess.Popen(
            [str(stub)],
            env=pg_env("postgresql+psycopg://aria:pw@db:5432/aria"),
            stdout=handle,
        )
        assert proc.wait() == 0
    with pytest.raises(AssertionError):
        _assert_real_gzip_wrapped_dump(destination, payload)


def test_backup_job_disabled_and_sqlite_guard(monkeypatch) -> None:
    import app.services.backup as backup_mod

    class _S:
        aria_backup_enabled = False
        aria_backup_dir = "backups"
        aria_backup_keep = 14
        aria_backup_encryption_key = None
        database_url = "sqlite://"

    monkeypatch.setattr(backup_mod, "get_settings", lambda: _S(), raising=False)
    import app.core.config as config

    real = config.get_settings
    monkeypatch.setattr(config, "get_settings", lambda: _S())
    # Disabled: no-op.
    assert backup_mod.run_backup_job() is False
    # Enabled with sqlite DATABASE_URL: refuses to run.
    _S.aria_backup_enabled = True
    try:
        backup_mod.run_backup_job()
    except backup_mod.BackupError as exc:
        assert "PostgreSQL" in str(exc)
    else:
        raise AssertionError("expected BackupError for sqlite DATABASE_URL")
    monkeypatch.setattr(config, "get_settings", real)


def test_migration_chain_has_rate_limit_buckets() -> None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    root = Path(__file__).resolve().parents[1]
    script = ScriptDirectory.from_config(Config(str(root / "alembic.ini")))
    assert len(script.get_heads()) == 1
    revisions = {revision.revision for revision in script.walk_revisions()}
    assert {"0016_rate_limit_buckets", "0019_roadmaps", "0020_chat_fallback"} <= revisions


def test_prod_compose_valid_and_routes_through_proxy() -> None:
    import tomllib  # noqa: F401 - placeholder to keep imports tidy

    import yaml

    repo = Path(__file__).resolve().parents[1]
    with (repo / "docker-compose.prod.yml").open("rb") as handle:
        compose = yaml.safe_load(handle)
    services = compose["services"]
    # Only the proxy publishes host ports; backend/frontend are internal.
    assert services["proxy"]["ports"] == ["80:80", "443:443"]
    assert "ports" not in services["backend"]
    assert "ports" not in services["frontend"]
    assert services["backend"]["expose"] == ["8000"]
    assert services["frontend"]["expose"] == ["3000"]
    # Shared limiter + backups wired by default in production.
    assert services["backend"]["environment"]["ARIA_RATE_LIMIT_BACKEND"] == "${ARIA_RATE_LIMIT_BACKEND:-db}"
    assert services["backend"]["environment"]["ARIA_BACKUP_ENABLED"] == "${ARIA_BACKUP_ENABLED:-true}"
    assert (
        services["backend"]["environment"]["ARIA_LLM_COMPLETION_RESERVE_TOKENS"]
        == "${ARIA_LLM_COMPLETION_RESERVE_TOKENS:-512}"
    )
    assert "backups:/backups" in services["backend"]["volumes"]
    caddyfile = (repo / "deploy" / "caddy" / "Caddyfile").read_text()
    assert "/api/*" in caddyfile and "reverse_proxy backend:8000" in caddyfile
    # "backend:8000/ready" is invalid Caddy syntax ("x/y" parses as
    # <network>/<address> and dials fail); /ready must reuse the plain
    # upstream since the request path is preserved.
    assert "backend:8000/ready" not in caddyfile
    assert "reverse_proxy frontend:3000" in caddyfile
