from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "aria-api"}


def test_request_id_is_returned() -> None:
    request_id = "test-request-123"
    response = TestClient(app).get("/health", headers={"x-request-id": request_id})
    assert response.headers["x-request-id"] == request_id


def test_readiness_checks_database_schema_not_only_connectivity(client, engine):
    from sqlalchemy import text

    assert client.get("/ready").status_code == 200
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE conversation_messages RENAME COLUMN fallback_used TO missing_column"))
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["database"] == "ok"
    assert response.json()["schema"] == "unavailable"
    assert "conversation_messages" not in response.text
    assert "missing_column" not in response.text
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE conversation_messages RENAME COLUMN missing_column TO fallback_used"))


def test_readiness_never_exposes_database_exception_detail(client, monkeypatch):
    from app.db.dependencies import get_db

    class FailedDatabase:
        def execute(self, *args):
            raise RuntimeError("postgresql://user:secret-password@private-host/internal_database")
        def rollback(self):
            pass
    app.dependency_overrides[get_db] = lambda: FailedDatabase()
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
    assert "secret-password" not in response.text
    assert "private-host" not in response.text


def test_production_settings_reject_missing_or_short_session_secret():
    import pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    for secret in (None, "short", "development-only-change-me"):
        with pytest.raises(ValidationError, match="dedicated session secret"):
            Settings(_env_file=None, aria_env="production", database_url="postgresql://localhost/aria",
                     aria_session_secret=secret, supabase_jwt_secret=None)
    settings = Settings(_env_file=None, aria_env="production", database_url="postgresql://localhost/aria",
                        aria_session_secret="s" * 32)
    assert settings.aria_env == "production"
