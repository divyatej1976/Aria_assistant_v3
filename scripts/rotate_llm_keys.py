"""Rotate BYO LLM key ciphertext to the primary encryption key.

Procedure:
  1. Generate a new key: python scripts/generate_llm_keys_key.py
  2. Set ARIA_LLM_KEYS_ENCRYPTION_KEY to the new value and
     ARIA_LLM_KEYS_ENCRYPTION_KEY_OLD to the previous value. Redeploy.
  3. Run this script. Repeat until it reports reencrypted=0 and failed=0.
  4. Remove ARIA_LLM_KEYS_ENCRYPTION_KEY_OLD. Redeploy.

Rows that fail to decrypt with either key are reported, never deleted.
"""

import sys
from pathlib import Path

# Make the script runnable from the repo root without PYTHONPATH=backend.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def main() -> int:
    from app.db.session import SessionLocal
    from app.services.llm_keys import reencrypt_with_primary

    db = SessionLocal()
    try:
        summary = reencrypt_with_primary(db)
    finally:
        db.close()
    print(
        f"total={summary['total']} "
        f"reencrypted={summary['reencrypted']} failed={summary['failed']}"
    )
    if summary["failed"]:
        print("Some rows could not be decrypted; _OLD key must be kept.", file=sys.stderr)
        return 1
    if summary["reencrypted"]:
        print("Re-run until reencrypted=0 before dropping the _OLD key.")
        return 2
    print("Rotation complete: safe to drop ARIA_LLM_KEYS_ENCRYPTION_KEY_OLD.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
