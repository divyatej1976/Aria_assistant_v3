"""Generate a Fernet encryption key for ARIA_LLM_KEYS_ENCRYPTION_KEY."""

import sys
from pathlib import Path

# Make the script runnable from the repo root without PYTHONPATH=backend.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.llm_keys import generate_encryption_key  # noqa: E402


def main() -> None:
    print(generate_encryption_key())


if __name__ == "__main__":
    main()
