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
