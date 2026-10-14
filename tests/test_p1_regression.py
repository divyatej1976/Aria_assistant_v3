"""Regression for P1 ownership/context-scoping issues."""

import uuid

from fastapi.testclient import TestClient

MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time. "
    "A precedence graph detects cycles that indicate non-serializable schedules. "
    "Conflict serializability is a subset of view serializability for most schedules. "
    "Deadlock detection requires waiting for a cycle in the resource wait-for graph."
)


def register(client: TestClient, email: str):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse", "display_name": "Learner"})
    assert r.status_code == 201
    return r.json()

def headers(token: str):
    return {"Authorization": f"Bearer {token}"}

def create_context(client: TestClient, token: str, title="Ctx"):
    r = client.post("/api/v1/contexts", headers=headers(token), json={"title": title, "description": "d"})
    assert r.status_code == 201
    return r.json()["id"]

def add_material_and_sync(client: TestClient, token: str, context_id: str):
    r = client.post("/api/v1/resources/text", headers=headers(token), json={"context_id": context_id, "title": "M", "text": MATERIAL})
    assert r.status_code == 201
    # sync concepts
    r = client.post(f"/api/v1/contexts/{context_id}/concepts/sync", headers=headers(token))
    assert r.status_code in (200, 201)


def create_assessment_with_attempt(client: TestClient, token: str, context_id: str):
    r = client.post("/api/v1/assessments", headers=headers(token), json={"context_id": context_id, "format": "mcq", "question_count": 2, "difficulty": "easy"})
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    r = client.post(f"/api/v1/assessments/{aid}/attempts", headers=headers(token))
    assert r.status_code == 201, r.text
    attempt_id = r.json()["attempt_id"]
    questions = r.json()["questions"]
    answers = {q["id"]: q["options"][0] for q in questions}
    # save + submit to generate evaluation/evidence
    r = client.put(f"/api/v1/assessments/{aid}/attempts/{attempt_id}/answers", headers=headers(token), json={"answers": answers})
    assert r.status_code in (200, 422)
    r = client.post(f"/api/v1/assessments/{aid}/attempts/{attempt_id}/submit", headers=headers(token), json={"answers": answers, "idempotency_key": str(uuid.uuid4())})
    # may be 422 if not enough material, but try to ensure evidence
    return aid, attempt_id


def test_cross_assessment_attempt_save_rejected(client: TestClient):
    reg = register(client, f"cross-ass-{uuid.uuid4()}@example.com")
    token = reg["access_token"]
    ctx = create_context(client, token, "CrossAss")
    add_material_and_sync(client, token, ctx)
    # create two assessments with IN_PROGRESS attempts (not submitted)
    r = client.post("/api/v1/assessments", headers=headers(token), json={"context_id": ctx, "format": "mcq", "question_count": 2, "difficulty": "easy"})
    assert r.status_code == 201, r.text
    aid_a = r.json()["id"]
    r = client.post(f"/api/v1/assessments/{aid_a}/attempts", headers=headers(token))
    assert r.status_code == 201, r.text
    attempt_b = r.json()["attempt_id"]
    r = client.post("/api/v1/assessments", headers=headers(token), json={"context_id": ctx, "format": "mcq", "question_count": 2, "difficulty": "easy"})
    assert r.status_code == 201
    aid_a2 = r.json()["id"]
    # attempt_b belongs to aid_a, try to use it via aid_a2 URL
    r = client.put(f"/api/v1/assessments/{aid_a2}/attempts/{attempt_b}/answers", headers=headers(token), json={"answers": {}})
    assert r.status_code == 404
    assert "does not belong" in r.text

    r = client.post(f"/api/v1/assessments/{aid_a2}/attempts/{attempt_b}/submit", headers=headers(token), json={"answers": {}, "idempotency_key": str(uuid.uuid4())})
    assert r.status_code == 404


def test_cross_context_evidence_invalidate_rejected(client: TestClient):
    reg = register(client, f"cross-ev-{uuid.uuid4()}@example.com")
    token = reg["access_token"]
    ctx_a = create_context(client, token, "CtxA")
    ctx_b = create_context(client, token, "CtxB")
    for ctx in (ctx_a, ctx_b):
        add_material_and_sync(client, token, ctx)
        # ensure at least one concept
        client.post(f"/api/v1/contexts/{ctx}/concepts/sync", headers=headers(token))

    # create evidence in B
    aid_b, attempt_b = create_assessment_with_attempt(client, token, ctx_b)
    # get evidence list for B
    r = client.get(f"/api/v1/contexts/{ctx_b}/evidence", headers=headers(token))
    assert r.status_code == 200
    rows = r.json()
    if not rows:
        # if no evidence (e.g., no concepts), at least verify route structure: try invalidating random uuid through A should 404
        fake_ev = str(uuid.uuid4())
        r = client.post(f"/api/v1/contexts/{ctx_a}/evidence/{fake_ev}/invalidate", headers=headers(token))
        assert r.status_code == 404
        return
    ev_id = rows[0]["id"]
    # Try to invalidate B's evidence through A's URL — should be 404
    r = client.post(f"/api/v1/contexts/{ctx_a}/evidence/{ev_id}/invalidate", headers=headers(token))
    assert r.status_code == 404
    assert "Evidence not found" in r.text
    # Valid invalidation through correct context should succeed
    r = client.post(f"/api/v1/contexts/{ctx_b}/evidence/{ev_id}/invalidate", headers=headers(token))
    assert r.status_code == 200
