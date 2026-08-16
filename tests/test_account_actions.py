"""Account actions: password reset and email verification flows."""

import re
from urllib.parse import unquote

from fastapi.testclient import TestClient

from app.security.secrets import get_session_secret
from app.security.tokens import create_action_token


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class CapturingProvider:
    """Records email bodies so tests can extract the action token."""

    def __init__(self):
        self.messages: list[tuple[str, str, str]] = []

    def send(self, *, recipient: str, subject: str, body: str) -> str:
        self.messages.append((recipient, subject, body))
        return "logged"


def _token_from_body(body: str) -> str:
    match = re.search(r"token=([^&\s]+)", body)
    assert match is not None, f"no token found in email body: {body}"
    return unquote(match.group(1))


def _verify_token(email: str) -> str:
    return create_action_token(
        secret=get_session_secret(), purpose="email_verify", email=email
    )


def test_password_reset_request_never_leaks_email_existence(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"}
    )
    assert response.status_code == 200
    assert "has been sent" in response.json()["detail"]


def test_password_reset_changes_password_and_revokes_sessions(
    client: TestClient, session_factory
) -> None:
    from app.services.account_actions import request_password_reset

    session = register(client, "reset@example.com")
    token = session["access_token"]

    provider = CapturingProvider()
    db = session_factory()
    try:
        request_password_reset(db, provider=provider, email="reset@example.com")
    finally:
        db.close()
    assert len(provider.messages) == 1
    reset_token = _token_from_body(provider.messages[0][2])

    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "email": "reset@example.com",
            "token": reset_token,
            "new_password": "new-horse-pass",
        },
    )
    assert confirm.status_code == 200

    assert client.get("/api/v1/auth/me", headers=headers(token)).status_code == 401

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "correct-horse"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "reset@example.com", "password": "new-horse-pass"},
    )
    assert new_login.status_code == 200


def test_password_reset_token_is_single_use(
    client: TestClient, session_factory
) -> None:
    from app.services.account_actions import request_password_reset

    register(client, "reset-replay@example.com")
    provider = CapturingProvider()
    db = session_factory()
    try:
        request_password_reset(db, provider=provider, email="reset-replay@example.com")
    finally:
        db.close()
    reset_token = _token_from_body(provider.messages[0][2])

    first = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "email": "reset-replay@example.com",
            "token": reset_token,
            "new_password": "new-horse-pass",
        },
    )
    assert first.status_code == 200

    replay = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "email": "reset-replay@example.com",
            "token": reset_token,
            "new_password": "other-horse-pass",
        },
    )
    assert replay.status_code == 422


def test_password_reset_rejects_invalid_or_expired_token(client: TestClient) -> None:
    register(client, "reset-invalid@example.com")
    bad = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "email": "reset-invalid@example.com",
            "token": "not-a-real-token",
            "new_password": "new-horse-pass",
        },
    )
    assert bad.status_code == 422

    expired = create_action_token(
        secret=get_session_secret(),
        purpose="password_reset",
        email="reset-invalid@example.com",
        ttl_seconds=-60,
    )
    expired_response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "email": "reset-invalid@example.com",
            "token": expired,
            "new_password": "new-horse-pass",
        },
    )
    assert expired_response.status_code == 422


def test_email_verification_flow(client: TestClient) -> None:
    session = register(client, "verify@example.com")
    token = session["access_token"]

    me = client.get("/api/v1/auth/me", headers=headers(token)).json()
    assert me["verified"] is False

    requested = client.post(
        "/api/v1/auth/verify-email/request", headers=headers(token)
    )
    assert requested.status_code == 200

    # Confirmation is public (no session required) and email-bound.
    confirmed = client.post(
        "/api/v1/auth/verify-email/confirm",
        json={"email": "verify@example.com", "token": _verify_token("verify@example.com")},
    )
    assert confirmed.status_code == 200

    me = client.get("/api/v1/auth/me", headers=headers(token)).json()
    assert me["verified"] is True


def test_email_verification_rejects_bad_token(client: TestClient) -> None:
    register(client, "verify-bad@example.com")
    response = client.post(
        "/api/v1/auth/verify-email/confirm",
        json={"email": "verify-bad@example.com", "token": "garbage"},
    )
    assert response.status_code == 422


def test_changing_email_clears_verification(client: TestClient) -> None:
    session = register(client, "reverify@example.com")
    token = session["access_token"]
    confirmed = client.post(
        "/api/v1/auth/verify-email/confirm",
        json={"email": "reverify@example.com", "token": _verify_token("reverify@example.com")},
    )
    assert confirmed.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers(token)).json()["verified"] is True

    updated = client.patch(
        "/api/v1/auth/profile",
        headers=headers(token),
        json={"email": "reverify-new@example.com"},
    )
    assert updated.status_code == 200

    me = client.get("/api/v1/auth/me", headers=headers(token)).json()
    assert me["email"] == "reverify-new@example.com"
    assert me["verified"] is False
