"""Guard test: core runtime dependencies must be importable.

A missing declared dependency (for example PyMuPDF on an environment that
skipped the editable install) surfaces here as one clear failure instead of
scattered ImportErrors across the suite.
"""

import importlib

CORE_DEPS = ("fitz", "litellm", "reportlab", "sqlalchemy", "fastapi", "psycopg")


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
