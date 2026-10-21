"""Shared test fixtures.

The same suite runs against SQLite (default, in-memory) or a real PostgreSQL
database when TEST_DATABASE_URL is set, so Postgres-specific behavior is never
hidden behind the SQLite stand-in.
"""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ARIA_SCHEDULER_ENABLED", "false")
# Force the deterministic LLM path for the whole suite unless a test opts in
# by constructing its own provider. A developer's real .env GROQ_API_KEY must
# not leak into tests: they assert deterministic generator behavior, and an
# ambient key would make them fire live LLM calls (flaky asserts, token
# burn). Empty string also matches CI, which runs without any key.
os.environ["GROQ_API_KEY"] = ""
# The same for an OpenAI/Gemini key in keys.env.
os.environ["ARIA_LLM_API_KEY"] = ""
os.environ["BLOB_READ_WRITE_TOKEN"] = ""  # tests store audio on local disk
os.environ["GEMINI_API_KEY"] = ""
os.environ["ARIA_LLM_PROVIDER"] = "groq"
os.environ["LLM_MODEL"] = "openai/gpt-oss-120b"
# Point the app-level engine (used by /ready probes) at the test database.
os.environ["DATABASE_URL"] = (
    os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL") or "sqlite://"
)

from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app


def _engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        return create_engine(url, pool_pre_ping=True)
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture()
def engine():
    engine = _engine()
    if engine.dialect.name == "postgresql":
        # Installing pgvector's image does not enable its type in each database.
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def client(engine, session_factory) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
