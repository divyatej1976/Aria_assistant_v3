"""Audit regression tests: stable embeddings + planner context filtering."""

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.ai.providers import DeterministicEmbeddingProvider


def test_deterministic_embedding_is_process_stable():
    """str.hash() is per-process seeded; the fallback must use a stable digest."""
    provider = DeterministicEmbeddingProvider()
    text = "functions loops arguments"
    vector = asyncio.run(provider.embed([text]))[0]

    expected = [0.0] * provider.dimension
    for token in text.lower().split():
        digest = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:8], "big")
        expected[digest % provider.dimension] += 1.0
    magnitude = sum(v * v for v in expected) ** 0.5 or 1.0
    expected = [v / magnitude for v in expected]

    assert vector == expected


def _register(client: TestClient, email: str) -> dict:
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-9", "display_name": "Learner"},
    )
    assert res.status_code == 201
    return res.json()


def _headers(body: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {body['access_token']}"}


def test_planner_upcoming_and_missed_filter_by_context(client: TestClient):
    body = _register(client, f"audit-{datetime.now(UTC).timestamp()}@example.com")
    hdrs = _headers(body)

    ctx_ids = []
    for title in ("Context A", "Context B"):
        res = client.post("/api/v1/contexts", headers=hdrs, json={"title": title})
        assert res.status_code == 201
        ctx_ids.append(res.json()["id"])

    due = datetime.now(UTC) + timedelta(days=3)
    for cid, exam_title in zip(ctx_ids, ("Exam A", "Exam B"), strict=True):
        res = client.post(
            "/api/v1/planner/deadlines",
            headers=hdrs,
            json={
                "context_id": cid,
                "title": exam_title,
                "due_at": due.isoformat(),
                "reminder_days_before": 1,
            },
        )
        assert res.status_code == 201

    # upcoming filtered by context A returns only A's exam
    upcoming_a = client.get(
        "/api/v1/planner/upcoming",
        headers=hdrs,
        params={"days": 14, "context_id": ctx_ids[0]},
    ).json()
    assert [d["title"] for d in upcoming_a] == ["Exam A"]

    # unfiltered still returns both (backward compatible)
    upcoming_all = client.get(
        "/api/v1/planner/upcoming", headers=hdrs, params={"days": 14}
    ).json()
    assert len(upcoming_all) == 2

    # missed: one overdue task per context
    past = datetime.now(UTC) - timedelta(days=1)
    for cid, task_title in zip(ctx_ids, ("Task A", "Task B"), strict=True):
        res = client.post(
            "/api/v1/planner/tasks",
            headers=hdrs,
            json={"context_id": cid, "title": task_title, "due_at": past.isoformat()},
        )
        assert res.status_code == 201

    missed_a = client.get(
        "/api/v1/missed", headers=hdrs, params={"context_id": ctx_ids[0]}
    )
    # route lives under /api/v1/planner
    if missed_a.status_code == 404:
        missed_a = client.get(
            "/api/v1/planner/missed",
            headers=hdrs,
            params={"context_id": ctx_ids[0]},
        )
    assert missed_a.status_code == 200
    titles = [t["title"] for t in missed_a.json()]
    assert titles == ["Task A"]