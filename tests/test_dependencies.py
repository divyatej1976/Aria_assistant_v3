"""Guard tests: runtime dependencies must be declared and importable.

A missing declared dependency (for example PyMuPDF on an environment that
skipped the editable install) surfaces here as one clear failure instead of
scattered ImportErrors across the suite.
"""

import importlib
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_DEPS = ("fitz", "litellm", "reportlab", "sqlalchemy", "fastapi", "psycopg")
DRIFT_GUARD_DEPS = (
    "multipart",
    "apscheduler",
    "pywebpush",
    "prometheus_client",
    "sentry_sdk",
    "pgvector",
)


def test_core_runtime_dependencies_importable() -> None:
    missing: list[str] = []
    for name in CORE_DEPS:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    assert not missing, (
        f"Missing runtime dependencies: {', '.join(missing)}. "
        "Install them with: pip install -r requirements-dev.txt"
    )


def test_phase12_runtime_dependencies_importable() -> None:
    missing: list[str] = []
    for name in DRIFT_GUARD_DEPS:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    assert not missing, (
        f"Missing Phase 12 runtime dependencies: {', '.join(missing)}. "
        "Install them with: pip install -r requirements-dev.txt"
    )


def _pyproject_dependencies() -> list[str]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    return data["project"]["dependencies"]


def _requirements_dev_packages() -> set[str]:
    text = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    return {line.split(">=")[0].split("==")[0].strip() for line in text.splitlines() if line}


def test_requirements_dev_covers_pyproject_runtime_deps() -> None:
    runtime = [dep.split(">=")[0].split("==")[0].strip() for dep in _pyproject_dependencies()]
    declared = _requirements_dev_packages()
    missing = [name for name in runtime if name not in declared]
    assert not missing, (
        f"requirements-dev.txt is missing runtime deps from pyproject.toml: {missing}. "
        "Keep the two files in sync."
    )


# Tests must use the shared engine/session_factory fixtures so the same suite
# runs against SQLite locally and real PostgreSQL in CI. Only these files may
# build their own engine, each for a documented reason:
_FIXTURE_EXEMPT = {
    "test_e2e_database.py": "E2E schema-reset tests must construct an obsolete disposable SQLite file",
    "test_study_retry.py": "local retry races need independent file-backed SQLite connections; PostgreSQL uses shared fixtures",
    # A real subprocess cannot reopen in-memory SQLite after exiting.
    # PostgreSQL uses the shared engine fixture; SQLite uses a disposable file.
    "test_workflow_process_crash.py": "worker exit/restart needs persistent cross-process state",
    # Threads share one in-memory DB poorly; the race test needs file-backed SQLite.
    "test_assessments.py": "concurrent-submit race test uses a file DB for threads",
    # A separate session must observe uncommitted-then-rolled-back state.
    "test_context_deletion_full.py": "rollback test needs cross-session visibility",
}


def test_no_bypassed_test_engines() -> None:
    """No test module may spin its own database engine except allowlisted ones."""
    offenders: list[str] = []
    for path in (ROOT / "tests").glob("test_*.py"):
        if path.name == Path(__file__).name:
            continue  # this guard only mentions the symbol, never calls it
        text = path.read_text(encoding="utf-8")
        if "create_engine(" in text and path.name not in _FIXTURE_EXEMPT:
            offenders.append(path.name)
    assert not offenders, (
        f"These test modules bypass the shared fixtures: {offenders}. "
        "Use the engine/session_factory fixtures so tests also run on PostgreSQL in CI."
    )


def test_fixture_exemptions_still_needed() -> None:
    """Exemptions must still contain their justification (no silent drift)."""
    for name in _FIXTURE_EXEMPT:
        text = (ROOT / "tests" / name).read_text(encoding="utf-8")
        assert "create_engine(" in text, (
            f"{name} no longer builds its own engine — remove it from _FIXTURE_EXEMPT"
        )
