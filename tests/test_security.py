"""Phase 12.1 security hardening: cookie sessions, CSRF, secrets, rate limiting."""

from fastapi.testclient import TestClient

from app.security.rate_limit import allow_request


def _register(client: TestClient, email: str = "sec@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse"},
    )
    assert response.status_code == 201
    return response.json()


def test_session_and_csrf_cookies_are_set_on_register(client: TestClient) -> None:
    _register(client)
    cookie_names = set(client.cookies.keys())
    assert "aria_session" in cookie_names
    assert "aria_csrf" in cookie_names


def test_cookie_authenticated_mutation_requires_csrf_token(client: TestClient) -> None:
    _register(client)
    assert "aria_csrf" in client.cookies

    rejected = client.patch(
        "/api/v1/auth/profile",
        json={"display_name": "Hacker"},
    )
    assert rejected.status_code == 403
    assert "CSRF" in rejected.json()["detail"]

    accepted = client.patch(
        "/api/v1/auth/profile",
        json={"display_name": "Safe Learner"},
        headers={"X-CSRF-Token": client.cookies["aria_csrf"]},
    )
    assert accepted.status_code == 200
    assert accepted.json()["display_name"] == "Safe Learner"


def test_bearer_authenticated_mutation_bypasses_csrf(client: TestClient) -> None:
    session = _register(client)
    response = client.patch(
        "/api/v1/auth/profile",
        json={"display_name": "Bearer User"},
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )
    assert response.status_code == 200


def test_signout_clears_auth_cookies(client: TestClient) -> None:
    _register(client)
    response = client.post(
        "/api/v1/auth/signout",
        headers={"X-CSRF-Token": client.cookies["aria_csrf"]},
    )
    assert response.status_code == 200
    assert "aria_session" not in client.cookies
    assert "aria_csrf" not in client.cookies


def test_readiness_and_health_are_unauthenticated(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_session_secret_fails_fast_in_production(monkeypatch) -> None:
    import app.security.secrets as secrets

    class ProdSettings:
        aria_env = "production"
        aria_session_secret = None
        supabase_jwt_secret = None

    monkeypatch.setattr(secrets, "get_settings", lambda: ProdSettings())
    try:
        secrets.get_session_secret()
    except RuntimeError as exc:
        assert "must be set" in str(exc)
    else:
        raise AssertionError("expected RuntimeError for missing production secret")


def test_session_secret_uses_configured_value(monkeypatch) -> None:
    import app.security.secrets as secrets

    class ProdSettings:
        aria_env = "production"
        aria_session_secret = "super-secret"
        supabase_jwt_secret = None

    monkeypatch.setattr(secrets, "get_settings", lambda: ProdSettings())
    assert secrets.get_session_secret() == "super-secret"


def test_sliding_window_limiter_enforces_limit() -> None:
    assert allow_request("t:key", limit=2, window_seconds=60) is True
    assert allow_request("t:key", limit=2, window_seconds=60) is True
    assert allow_request("t:key", limit=2, window_seconds=60) is False
    assert allow_request("t:other", limit=2, window_seconds=60) is True


def test_rate_limit_dependency_inactive_in_development(
    client: TestClient,
) -> None:
    # ARIA_ENV defaults to development in tests, so no 429s are raised.
    for _ in range(30):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "correct-horse"},
        )
        assert response.status_code in (401, 422)
