"""Run the isolated local backend for externally managed Playwright checks."""

import os
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    sys.path.insert(0, str(root / "backend"))
    # Match the normal runner's local fallbacks without inheriting cloud keys.
    os.environ.update({
        "DATABASE_URL": os.environ.get("ARIA_TEST_DATABASE_URL", "sqlite:///./aria-frontend-magic-integration.db"),
        "ARIA_CORS_ORIGINS": os.environ.get("ARIA_TEST_ORIGIN", "http://localhost:3100"),
        "ARIA_SCHEDULER_ENABLED": "false",
        "GROQ_API_KEY": "",
        "ARIA_TTS_API_KEY": "",
        "ARIA_STT_API_KEY": "",
        "ARIA_EMBEDDING_API_KEY": "",
        "ARIA_AUDIO_DIR": "audiofiles",
        "ARIA_LLM_KEYS_ENCRYPTION_KEY": "BcxusO8Zc5ehRqVpEJWCJ_zsEkhJYLh5GHtBs344Jp0=",
    })
    import uvicorn
    from sqlalchemy import create_engine

    from app.db.base import Base
    from app.main import app

    engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    engine.dispose()
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("ARIA_TEST_PORT", "8010")))


if __name__ == "__main__":
    main()
