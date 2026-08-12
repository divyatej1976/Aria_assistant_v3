"""Shared test fixtures.

The same suite runs against SQLite (default, in-memory) or a real PostgreSQL
database when TEST_DATABASE_URL is set, so Postgres-specific behavior is never
hidden behind the SQLite stand-in.
"""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

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
def client() -> Generator[TestClient, None, None]:
    engine = _engine()
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

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
    Base.metadata.drop_all(engine)
    engine.dispose()
