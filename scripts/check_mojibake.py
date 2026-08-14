"""Fail if source files contain mojibake (mis-decoded UTF-8).

Scans frontend/backend/tests/scripts/docs for the common Latin-1 misdecoding
artifacts of valid UTF-8 (e.g. em-dash shown as `â€"`, middle dot as `Â·`) and
for files that are not valid UTF-8 at all. Exit code 1 reports any issues.

Usage:
    python scripts/check_mojibake.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = Path(__file__).resolve()
BAD_PATTERNS = (
    "\u00e2\u20ac",  # "â€" - em dash decoded as Latin-1
    "\u00c2\u00b7",  # "Â·" - middle dot decoded as Latin-1
    "\u00c3",  # "Ã" - start of a 2-byte UTF-8 char read as Latin-1
    "\u00c2 ",  # "Â " - misplaced circumflex before a space
    "\ufffd",  # U+FFFD replacement character
)
SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".css", ".md", ".py", ".yml", ".yaml", ".toml", ".json"}
SKIP_DIRS = {
    "node_modules",
    ".next",
    ".venv",
    "venv",
    ".git",
    "test-results",
    "playwright-report",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "backups",
    "postgres-data",
}


def scan(bases: list[Path]) -> list[str]:
    issues: list[str] = []
    for base in bases:
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
            for filename in filenames:
                if Path(filename).suffix not in SOURCE_SUFFIXES:
                    continue
                path = Path(dirpath) / filename
                if path.resolve() == SCRIPT_PATH:
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    issues.append(f"{path}: not valid UTF-8")
                    continue
                for pattern in BAD_PATTERNS:
                    if pattern in text:
                        issues.append(f"{path}: mojibake pattern {pattern!r}")
    return issues


def main() -> int:
    bases = [
        ROOT / "frontend",
        ROOT / "backend",
        ROOT / "tests",
        ROOT / "scripts",
        ROOT / "docs",
    ]
    issues = scan(bases)
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        print(f"{len(issues)} mojibake issue(s) found", file=sys.stderr)
        return 1
    print("No mojibake found in source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
