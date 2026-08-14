"""Guard test: no mojibake (mis-decoded UTF-8) in source or docs."""

from pathlib import Path

from scripts.check_mojibake import scan


def test_no_mojibake_in_source() -> None:
    root = Path(__file__).resolve().parents[1]
    bases = [
        root / "frontend",
        root / "backend",
        root / "tests",
        root / "scripts",
        root / "docs",
    ]
    issues = scan(bases)
    assert not issues, "\n".join(issues)
