"""Roadmaps remember the learner's weekly study time and pass it to the generator."""

import uuid

from fastapi.testclient import TestClient
from tests.test_assessments import create_context, headers, register


def test_weekly_time_is_saved_and_shapes_the_timeframe(client: TestClient, monkeypatch) -> None:
    import app.services.roadmap as roadmap_service

    seen: dict[str, str | None] = {}
    real = roadmap_service.generate_roadmap_tree

    async def capture(goal, level="Beginner", target_date=None, **kwargs):
        seen["target_date"] = target_date
        return await real(goal, level, target_date, **kwargs)

    monkeypatch.setattr(roadmap_service, "generate_roadmap_tree", capture)
    token = register(client, f"plan-{uuid.uuid4().hex[:8]}@example.com")["access_token"]
    h = headers(token)
    cid = create_context(client, token)

    created = client.post("/api/v1/roadmaps", headers=h, json={
        "goal": "Build a REST API", "level": "Beginner", "hours_per_week": 4, "context_id": cid,
    })
    assert created.status_code in (200, 201), created.text
    assert created.json()["hours_per_week"] == 4
    assert seen["target_date"] == "Self-paced (about 4 hours of study per week)"
    listed = client.get(f"/api/v1/roadmaps?context_id={cid}", headers=h).json()
    assert listed[0]["hours_per_week"] == 4


def test_weekly_time_is_optional_and_bounded(client: TestClient) -> None:
    token = register(client, f"plan-{uuid.uuid4().hex[:8]}@example.com")["access_token"]
    h = headers(token)
    without = client.post("/api/v1/roadmaps", headers=h, json={"goal": "Learn SQL"})
    assert without.status_code in (200, 201) and without.json()["hours_per_week"] is None
    assert client.post("/api/v1/roadmaps", headers=h, json={"goal": "Learn SQL", "hours_per_week": 0}).status_code == 422
