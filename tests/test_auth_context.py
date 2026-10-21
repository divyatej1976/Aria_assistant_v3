from fastapi.testclient import TestClient


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-9", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def test_register_login_me_and_context_creation(client: TestClient) -> None:
    session = register(client, "learner@example.com")
    headers = {"Authorization": f"Bearer {session['access_token']}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "learner@example.com"

    context = client.post(
        "/api/v1/contexts",
        headers=headers,
        json={"title": "DBMS", "description": "Transactions and serializability"},
    )
    assert context.status_code == 201
    assert context.json()["title"] == "DBMS"

    listed = client.get("/api/v1/contexts", headers=headers)
    assert [item["title"] for item in listed.json()] == ["DBMS"]

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "learner@example.com", "password": "correct-horse-9"},
    )
    assert login.status_code == 200


def test_contexts_are_isolated_between_learners(client: TestClient) -> None:
    first = register(client, "first@example.com")
    first_headers = {"Authorization": f"Bearer {first['access_token']}"}
    client.post("/api/v1/contexts", headers=first_headers, json={"title": "Private context"})

    second = register(client, "second@example.com")
    second_headers = {"Authorization": f"Bearer {second['access_token']}"}
    listed = client.get("/api/v1/contexts", headers=second_headers)
    assert listed.status_code == 200
    assert listed.json() == []


def test_protected_context_endpoint_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/contexts")
    assert response.status_code == 401
