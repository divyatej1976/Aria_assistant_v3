"""Phase 12.1 security hardening: cookie sessions, CSRF, secrets, rate limiting."""

import asyncio
import time

from fastapi.testclient import TestClient

from app.security.rate_limit import _hits, allow_request, allow_request_db


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


def test_csrf_cookie_outlives_browser_close_like_session(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "ttl@example.com", "password": "correct-horse"},
    )
    cookies = {h.split("=", 1)[0]: h for h in response.headers.get_list("set-cookie")}
    assert "Max-Age=86400" in cookies["aria_session"]
    assert "Max-Age=86400" in cookies["aria_csrf"]


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


def test_cookie_only_login_omits_bearer_token(client: TestClient) -> None:
    """?bearer=false is the browser contract: session cookie set, no token body."""
    _register(client, email="cookieonly@example.com")
    response = client.post(
        "/api/v1/auth/login?bearer=false",
        json={"email": "cookieonly@example.com", "password": "correct-horse"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"] is None
    assert "aria_session" in response.cookies

    default = client.post(
        "/api/v1/auth/login",
        json={"email": "cookieonly@example.com", "password": "correct-horse"},
    )
    assert default.status_code == 200
    assert default.json()["access_token"]


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


def test_cors_preflight_allows_api_headers(client: TestClient) -> None:
    """Every non-simple header the frontend may send must survive preflight.

    Regression guard for the CORS allowlist: if a new custom header is added
    client-side but not here, cross-origin calls fail before reaching the API.
    """
    response = client.options(
        "/api/v1/orchestration/workflows/study-plan",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": (
                "Content-Type, X-CSRF-Token, Idempotency-Key, Authorization"
            ),
        },
    )
    assert response.status_code == 200
    allowed = response.headers.get("access-control-allow-headers", "").lower()
    for header in ("content-type", "x-csrf-token", "idempotency-key", "authorization"):
        assert header in allowed, f"{header} missing from CORS allow-headers: {allowed}"


def _csrf_probe(cookie: bytes, csrf_header: bytes) -> tuple[int, bool]:
    """Drive CSRFMiddleware directly with raw ASGI scope (byte-exact headers)."""
    from app.security.csrf import CSRFMiddleware

    reached: list[bool] = []

    async def inner(_scope, _receive, send) -> None:
        reached.append(True)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})

    async def run() -> int:
        statuses: list[int] = []

        async def send(message) -> None:
            if message["type"] == "http.response.start":
                statuses.append(message["status"])

        async def receive():
            return {}

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/study/sessions",
            "headers": [(b"cookie", cookie), (b"x-csrf-token", csrf_header)],
        }
        await CSRFMiddleware(inner)(scope, receive, send)
        return statuses[0]

    return asyncio.run(run()), bool(reached)


def test_csrf_wrong_token_rejected() -> None:
    status, reached = _csrf_probe(b"aria_session=abc; aria_csrf=tok123", b"nope")
    assert (status, reached) == (403, False)


def test_csrf_non_ascii_token_rejected_without_500() -> None:
    """Attacker-controlled bytes must yield 403, never a TypeError 500."""
    status, reached = _csrf_probe(
        b"aria_session=abc; aria_csrf=tok123", "tökün❌".encode()
    )
    assert (status, reached) == (403, False)


def test_csrf_valid_token_passes() -> None:
    status, reached = _csrf_probe(b"aria_session=abc; aria_csrf=tok123", b"tok123")
    assert (status, reached) == (200, True)


def test_memory_limiter_evicts_dead_keys() -> None:
    now = time.monotonic()
    added = [f"t:evict-expired-{i}" for i in range(10_200)]
    try:
        for key in added:
            _hits[key].append(now - 3_600)  # long expired for a 60s window
        assert allow_request("t:evict-probe", limit=5, window_seconds=60) is True
        assert len(_hits) <= 11_000
    finally:
        for key in added + ["t:evict-probe"]:
            _hits.pop(key, None)


def test_memory_limiter_hard_caps_fresh_key_flood() -> None:
    now = time.monotonic()
    added = [f"t:evict-fresh-{i}" for i in range(10_900)]
    try:
        for key in added:
            _hits[key].append(now)  # fresh: expired-sweep cannot remove these
        assert allow_request("t:evict-probe2", limit=5, window_seconds=60) is True
        assert len(_hits) <= 11_000
    finally:
        for key in added + ["t:evict-probe2"]:
            _hits.pop(key, None)


def test_db_limiter_fails_open_on_infra_error() -> None:
    def broken_factory():
        raise ConnectionError("db down")

    assert (
        allow_request_db(
            "t:broken", limit=1, window_seconds=60, session_factory=broken_factory
        )
        is True
    )
