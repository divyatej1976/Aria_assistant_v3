"""Maintain audio storage or requeue missing files after a database-only restore."""

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--sweep", action="store_true", help="Remove old unreferenced UUID files")
    action.add_argument("--requeue-missing", action="store_true", help="Queue missing ready audio for regeneration")
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    from app.db.session import SessionLocal
    from app.services.audio import requeue_missing_audio, sweep_audio_files

    with SessionLocal() as db:
        if args.sweep:
            print(sweep_audio_files(db))
        else:
            print(f"Queued {requeue_missing_audio(db)} missing audio artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
