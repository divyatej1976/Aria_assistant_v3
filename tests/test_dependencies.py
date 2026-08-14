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
