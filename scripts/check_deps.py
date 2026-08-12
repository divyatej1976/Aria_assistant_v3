"""Verify every declared dependency is importable.

Exit code is non-zero when anything is missing, so CI or a local reviewer can
diagnose a provisioning gap in seconds:

    python scripts/check_deps.py
    pip install -r requirements-dev.txt
"""

import importlib
import sys


def _utf8_stdout() -> None:
    """Make prints safe on Windows consoles with non-ASCII paths (cp1252)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_utf8_stdout()

MODULES = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pydantic-settings": "pydantic_settings",
    "sqlalchemy": "sqlalchemy",
    "alembic": "alembic",
    "psycopg": "psycopg",
    "pymupdf": "pymupdf",
    "fitz": "fitz",
    "litellm": "litellm",
    "reportlab": "reportlab",
    "httpx": "httpx",
    "pytest": "pytest",
    "pytest-asyncio": "pytest_asyncio",
    "ruff": "ruff",
    "mypy": "mypy",
}


def main() -> int:
    print(f"Interpreter: {sys.executable}")
    missing: list[str] = []
    for label, module in MODULES.items():
        try:
            importlib.import_module(module)
        except ImportError:
            print(f"MISSING {label}")
            missing.append(label)
        else:
            print(f"OK      {label}")
    if missing:
        print(f"\nMissing dependencies: {', '.join(missing)}")
        print("Install them with:  pip install -r requirements-dev.txt")
        return 1
    print("\nAll declared dependencies are importable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
