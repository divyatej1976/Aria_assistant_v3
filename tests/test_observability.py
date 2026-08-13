"""Phase 12.4 observability: metrics endpoint, readiness probes, request logging."""

from fastapi.testclient import TestClient

from app.core.metrics import normalize_path, observe_request


def test_metrics_endpoint_exposes_prometheus_text(client: TestClient) -> None:
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "aria_http_requests_total" in response.text


def test_readiness_reports_database_and_probes(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"
    assert body["ai_provider"] in ("configured", "not_configured")
    assert body["scheduler"] in ("running", "idle")


def test_normalize_path_groups_uuids_and_numbers() -> None:
    assert normalize_path("/api/v1/workflows/3c6d5b1a-0000-0000-0000-000000000000") == (
        "/api/v1/workflows/{id}"
    )
    assert normalize_path("/api/v1/contexts/42") == "/api/v1/contexts/{n}"
    assert normalize_path("/api/v1/contexts") == "/api/v1/contexts"


def test_observe_request_records_labels() -> None:
    observe_request(method="GET", path="/api/v1/health", status=200, duration_ms=12)
    from app.core.metrics import http_requests_total

    value = http_requests_total.labels(method="GET", path="/api/v1/health", status="200")
    assert value._value.get() >= 1
