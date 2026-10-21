"""Each roadmap topic has sub-topics the learner ticks off, like roadmap.sh."""

import uuid

from fastapi.testclient import TestClient
from tests.test_assessments import create_context, headers, register


def _roadmap(client: TestClient) -> tuple[dict, dict]:
    token = register(client, f"subtopics-{uuid.uuid4().hex[:8]}@example.com")["access_token"]
    h = headers(token)
    cid = create_context(client, token)
    created = client.post("/api/v1/roadmaps", headers=h, json={"goal": "Data structures", "level": "Beginner",
                                                                "context_id": cid})
    assert created.status_code in (200, 201), created.text
    return h, created.json()


def test_subtopics_tick_untick_and_stay_scoped(client: TestClient) -> None:
    h, roadmap = _roadmap(client)
    topic = roadmap["tiers"][0]["topics"][0]
    skill = topic["key_skills"][0]
    url = f"/api/v1/roadmaps/{roadmap['id']}/milestones/{topic['id']}/skills"

    ticked = client.put(url, headers=h, json={"skill": skill, "done": True})
    assert ticked.status_code == 200, ticked.text
    assert ticked.json()["tiers"][0]["topics"][0]["done_skills"] == [skill]
    # Ticking twice keeps one entry; unticking clears it; the change survives a reload.
    client.put(url, headers=h, json={"skill": skill, "done": True})
    assert client.get(f"/api/v1/roadmaps/{roadmap['id']}", headers=h).json()["tiers"][0]["topics"][0]["done_skills"] == [skill]
    cleared = client.put(url, headers=h, json={"skill": skill, "done": False})
    assert cleared.json()["tiers"][0]["topics"][0]["done_skills"] == []

    assert client.put(url, headers=h, json={"skill": "Not a sub-topic", "done": True}).status_code == 404
    other_h, _ = _roadmap(client)
    assert client.put(url, headers=other_h, json={"skill": skill, "done": True}).status_code == 404
