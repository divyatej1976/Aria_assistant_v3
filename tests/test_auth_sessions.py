import base64
import json
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.security.tokens import create_session_token


def register(client: TestClient, email: str, *, device: str | None = None) -> dict[str, str]:
    body = {"email": email, "password": "correct-horse", "display_name": "Learner"}
    if device:
        body["device_label"] = device
    response = client.post("/api/v1/auth/register", json=body)
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, email: str, *, device: str | None = None) -> dict[str, str]:
    body = {"email": email, "password": "correct-horse"}
    if device:
        body["device_label"] = device
    response = client.post("/api/v1/auth/login", json=body)
    assert response.status_code == 200
    return response.json()


def session_id_from_token(token: str) -> UUID:
    encoded = token.split(".", 1)[0]
    payload = json.loads(base64.urlsafe_b64decode(encoded.encode()))
    return UUID(payload["sid"])


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_signout_revokes_only_that_session(client: TestClient) -> None:
    first = register(client, "multi@example.com", device="laptop")
    second = login(client, "multi@example.com", device="phone")

    signed_out = client.post("/api/v1/auth/signout", headers=headers(first["access_token"]))
    assert signed_out.status_code == 200

    assert client.get("/api/v1/auth/me", headers=headers(first["access_token"])).status_code == 401
    assert client.get("/api/v1/auth/me", headers=headers(second["access_token"])).status_code == 200


def test_revoke_other_session_from_session_list(client: TestClient) -> None:
    register(client, "devices@example.com", device="laptop")
    phone = login(client, "devices@example.com", device="phone")

    listing = client.get("/api/v1/auth/sessions", headers=headers(phone["access_token"]))
    assert listing.status_code == 200
    active = listing.json()
    assert len(active) == 2
    current = next(item for item in active if item["is_current"])
    other = next(item for item in active if not item["is_current"])
    assert current["device_label"] == "phone"
    assert other["device_label"] == "laptop"

    revoked = client.post(
        f"/api/v1/auth/sessions/{other['id']}/revoke", headers=headers(phone["access_token"])
    )
    assert revoked.status_code == 200
    assert (
        client.get("/api/v1/auth/me", headers=headers(phone["access_token"])).status_code == 200
    )
    listing = client.get("/api/v1/auth/sessions", headers=headers(phone["access_token"]))
    assert [item["device_label"] for item in listing.json()] == ["phone"]


def test_cannot_revoke_current_session_via_revoke_endpoint(client: TestClient) -> None:
    session = register(client, "current@example.com")
    response = client.post(
        f"/api/v1/auth/sessions/{session_id_from_token(session['access_token'])}/revoke",
        headers=headers(session["access_token"]),
    )
    assert response.status_code == 400
    me = client.get("/api/v1/auth/me", headers=headers(session["access_token"]))
    assert me.status_code == 200


def test_password_change_revokes_other_sessions_keeps_current(client: TestClient) -> None:
    first = register(client, "passwd@example.com")
    second = login(client, "passwd@example.com")

    changed = client.post(
        "/api/v1/auth/password",
        headers=headers(first["access_token"]),
        json={"current_password": "correct-horse", "new_password": "new-horse-pass"},
    )
    assert changed.status_code == 200

    assert client.get("/api/v1/auth/me", headers=headers(first["access_token"])).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers(second["access_token"])).status_code == 401

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "passwd@example.com", "password": "correct-horse"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "passwd@example.com", "password": "new-horse-pass"},
    )
    assert new_login.status_code == 200


def test_data_reset_deletes_owned_data_and_isolates_other_learner(client: TestClient) -> None:
    first = register(client, "first-reset@example.com")
    second = register(client, "second-reset@example.com")
    client.post(
        "/api/v1/contexts",
        headers=headers(first["access_token"]),
        json={"title": "First learner context"},
    )
    client.post(
        "/api/v1/contexts",
        headers=headers(second["access_token"]),
        json={"title": "Second learner context"},
    )

    reset = client.delete("/api/v1/account/data", headers=headers(first["access_token"]))
    assert reset.status_code == 200
    # Honest scope: the response must disclose retained security/audit records.
    detail = reset.json()["detail"]
    assert "All learning data deleted" in detail
    assert "retained" in detail and "audit" in detail

    assert (
        client.get("/api/v1/auth/me", headers=headers(first["access_token"])).status_code == 401
    )
    assert (
        client.get("/api/v1/auth/me", headers=headers(second["access_token"])).status_code == 200
    )

    first_again = login(client, "first-reset@example.com")
    listed_first = client.get("/api/v1/contexts", headers=headers(first_again["access_token"]))
    assert listed_first.json() == []
    listed_second = client.get("/api/v1/contexts", headers=headers(second["access_token"]))
    assert [item["title"] for item in listed_second.json()] == ["Second learner context"]


def test_expired_token_is_rejected(client: TestClient) -> None:
    session = register(client, "expired@example.com")
    settings = get_settings()
    secret = settings.supabase_jwt_secret or "development-only-change-me"
    expired = create_session_token(
        session_id=session_id_from_token(session["access_token"]), secret=secret, ttl_seconds=-3600
    )
    response = client.get("/api/v1/auth/me", headers=headers(expired))
    assert response.status_code == 401


def test_auth_failures_do_not_leak_details(client: TestClient) -> None:
    register(client, "leak@example.com")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "leak@example.com", "password": "wrong-password"},
    )
    assert login.status_code == 401
    assert login.json()["detail"] == "Invalid credentials"

    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "leak@example.com", "password": "correct-horse"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Email already registered"
