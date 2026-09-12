"""Invalid UUID should be 422, valid UUID works, cross-learner returns 404/ownership."""

import uuid

import pytest
from fastapi.testclient import TestClient


def register(client: TestClient, email: str) -> tuple[str, str]:
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse", "display_name": "Learner"})
    assert r.status_code == 201
    token = r.json()["access_token"]
    return token, email

def headers(token: str):
    return {"Authorization": f"Bearer {token}"}

def create_context(client: TestClient, token: str) -> str:
    r = client.post("/api/v1/contexts", headers=headers(token), json={"title": "Ctx", "description": "d"})
    assert r.status_code == 201
    return r.json()["id"]

INVALID = "not-a-uuid"
VALID_RANDOM = str(uuid.uuid4())


@pytest.mark.parametrize("method,url_factory", [
    ("POST", lambda cid: "/api/v1/notes"),
    ("GET", lambda cid: f"/api/v1/notes?context_id={cid}"),
    ("GET", lambda cid: f"/api/v1/notes/due?context_id={cid}"),
    ("POST", lambda cid: "/api/v1/notes/generate"),
    ("POST", lambda cid: "/api/v1/resources/text"),
    ("POST", lambda cid: "/api/v1/resources/pdf"),
    ("GET", lambda cid: f"/api/v1/resources?context_id={cid}"),
    ("GET", lambda cid: f"/api/v1/assessments?context_id={cid}"),
    ("POST", lambda cid: "/api/v1/assessments"),
    ("GET", lambda cid: f"/api/v1/study/sessions?context_id={cid}"),
    ("POST", lambda cid: "/api/v1/study/sessions"),
    ("GET", lambda cid: f"/api/v1/planner/deadlines?context_id={cid}"),
    ("GET", lambda cid: f"/api/v1/planner/tasks?context_id={cid}"),
    ("GET", lambda cid: f"/api/v1/planner/upcoming?context_id={cid}"),
    ("GET", lambda cid: f"/api/v1/planner/missed?context_id={cid}"),
])
def test_invalid_uuid_returns_422(client: TestClient, method, url_factory):
    token, _ = register(client, f"inv-{uuid.uuid4()}@example.com")
    url = url_factory(INVALID)
    if method == "POST":
        body = {"context_id": INVALID, "title": "t", "body": "b", "text": "t", "format": "mcq", "mode": "BASELINE"}
        # choose minimal valid body per endpoint – most will still fail validation for other fields but UUID validation triggers first
        if "notes/generate" in url:
            body = {"context_id": INVALID}
        elif "assessments" in url and url == "/api/v1/assessments":
            body = {"context_id": INVALID, "format": "mcq", "question_count": 1}
        elif "study" in url:
            body = {"context_id": INVALID, "mode": "BASELINE"}
        elif "planner" in url:
            body = {"context_id": INVALID, "title": "t", "due_at": "2030-01-01T00:00:00Z"}
        elif "resources/text" in url:
            body = {"context_id": INVALID, "title": "t", "text": "hi"}
        elif "resources/pdf" in url:
            # pdf endpoint uses query param, not body
            r = client.post(url, headers=headers(token))
            assert r.status_code == 422
            return
        r = client.request(method, url, headers=headers(token), json=body)
    else:
        r = client.request(method, url, headers=headers(token))
    assert r.status_code == 422, f"{method} {url} expected 422 got {r.status_code} {r.text}"
    assert "uuid" in r.text.lower()


def test_valid_uuid_still_works(client: TestClient):
    token, _ = register(client, f"valid-{uuid.uuid4()}@example.com")
    ctx = create_context(client, token)
    # Each valid endpoint should succeed (or at least not 422 for UUID parsing)
    r = client.post("/api/v1/notes", headers=headers(token), json={"context_id": ctx, "title": "t", "body": "b"})
    assert r.status_code == 201
    r = client.get(f"/api/v1/notes?context_id={ctx}", headers=headers(token))
    assert r.status_code == 200
    r = client.post("/api/v1/resources/text", headers=headers(token), json={"context_id": ctx, "title": "t2", "text": "hello"})
    assert r.status_code == 201
    r = client.get(f"/api/v1/resources?context_id={ctx}", headers=headers(token))
    assert r.status_code == 200
    r = client.post("/api/v1/study/sessions", headers=headers(token), json={"context_id": ctx, "mode": "BASELINE"})
    assert r.status_code == 201
    r = client.get(f"/api/v1/study/sessions?context_id={ctx}", headers=headers(token))
    assert r.status_code == 200


def test_cross_learner_uuid_returns_404(client: TestClient):
    token_a, _ = register(client, f"a-{uuid.uuid4()}@example.com")
    token_b, _ = register(client, f"b-{uuid.uuid4()}@example.com")
    ctx_a = create_context(client, token_a)
    # B tries to use A's context_id – should be 404 ownership, not 422
    r = client.get(f"/api/v1/notes?context_id={ctx_a}", headers=headers(token_b))
    assert r.status_code == 404
    r = client.get(f"/api/v1/resources?context_id={ctx_a}", headers=headers(token_b))
    assert r.status_code == 404
    r = client.get(f"/api/v1/study/sessions?context_id={ctx_a}", headers=headers(token_b))
    assert r.status_code == 404


def test_invalid_concept_id_and_list_uuid_returns_422(client: TestClient):
    token, _ = register(client, f"conc-{uuid.uuid4()}@example.com")
    ctx = create_context(client, token)
    r = client.post("/api/v1/notes", headers=headers(token), json={"context_id": ctx, "title": "t", "body": "b", "concept_id": "bad-uuid"})
    assert r.status_code == 422
    r = client.post("/api/v1/assessments", headers=headers(token), json={"context_id": ctx, "format": "mcq", "concept_ids": ["bad-uuid"]})
    assert r.status_code == 422
    # Prerequisite
    # Need two concepts to test prerequisite
    _r1 = client.post("/api/v1/contexts", headers=headers(token), json={"title": "Ctx2"})
    # Instead use adaptation prerequisite endpoint – need concept ids, create via sync
    # Use the previously created ctx's concepts via sync
    client.post(f"/api/v1/contexts/{ctx}/concepts/sync", headers=headers(token))
    concepts = client.get(f"/api/v1/contexts/{ctx}/concepts", headers=headers(token)).json()
    if len(concepts) >= 1:
        cid = concepts[0]["id"]
        r = client.post(f"/api/v1/contexts/{ctx}/concepts/{cid}/prerequisites", headers=headers(token), json={"prerequisite_concept_id": "not-a-uuid"})
        assert r.status_code == 422
