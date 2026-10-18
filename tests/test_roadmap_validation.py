import asyncio
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.schemas.roadmap import GeneratedRoadmapTree
from app.services.roadmap import generate_roadmap_tree


def tree():
    return {"goal": "Biology", "level": "Beginner", "phases": [
        {"phase_name": "Foundations", "milestones": [
            {"title": "Cells", "description": "Learn cell structures", "key_skills": ["Cells"], "prerequisites": []},
            {"title": "Genetics", "description": "Learn inheritance", "key_skills": ["Genetics"], "prerequisites": ["Cells"]},
        ]},
        {"phase_name": "Core Concepts", "milestones": [
            {"title": "Systems", "description": "Connect systems", "key_skills": [], "prerequisites": ["Genetics"]}]},
        {"phase_name": "Advanced Topics", "milestones": [
            {"title": "Experiments", "description": "Apply research", "key_skills": [], "prerequisites": ["Systems"]}]},
        {"phase_name": "Mastery Track", "milestones": [
            {"title": "Demonstration", "description": "Explain results", "key_skills": [], "prerequisites": ["Experiments"]}]},
    ]}


@pytest.mark.parametrize("outcome,mode,reason", [
    ("success", "ai", None),
    ("missing", "starter", "provider_unavailable"),
    ("failure", "starter", "provider_failed"),
    ("invalid", "starter", "invalid_output"),
])
def test_roadmap_provenance_survives_create_list_and_reload(client, monkeypatch, outcome, mode, reason):
    class Provider:
        async def generate_structured(self, **kwargs):
            if outcome == "failure":
                raise RuntimeError("private provider prompt and key")
            payload = tree()
            if outcome == "invalid":
                payload["phases"] = []
            # Provider-authored provenance cannot override application facts.
            payload["generation_mode"] = "starter"
            payload["fallback_reason"] = "private provider detail"
            return payload

    provider = None if outcome == "missing" else Provider()
    monkeypatch.setattr("app.services.roadmap.get_llm_provider_for_owner", lambda *args, **kwargs: provider)
    monkeypatch.setattr("app.ai.registry.get_llm_provider", lambda: provider)
    registered = client.post("/api/v1/auth/register", json={
        "email": f"roadmap-origin-{outcome}@example.com", "password": "roadmap-password",
    })
    headers = {"Authorization": "Bearer " + registered.json()["access_token"]}
    created = client.post("/api/v1/roadmaps", headers=headers, json={"goal": "Biology"})
    assert created.status_code == 201
    roadmap_id = created.json()["id"]
    responses = [created.json(), client.get(f"/api/v1/roadmaps/{roadmap_id}", headers=headers).json(),
                 client.get("/api/v1/roadmaps", headers=headers).json()[0]]
    for response in responses:
        assert response["generation_mode"] == mode
        assert response["fallback_reason"] == reason
        assert "private provider" not in str(response)


@pytest.mark.parametrize("bad", ["skill_length", "blank_skill", "duplicate_skills", "duplicate_title",
                                 "unknown_prerequisite", "forward_prerequisite", "self_prerequisite",
                                 "duplicate_prerequisites", "duplicate_phase", "phase_order", "blank_title",
                                 "blank_description", "goal_length", "title_length", "invalid_level", "missing_phase"])
def test_provider_tree_rejects_ambiguous_unbounded_or_unresolvable_output(bad):
    value = tree()
    first, second = value["phases"][0]["milestones"]
    if bad == "skill_length":
        first["key_skills"] = ["x" * 129]
    elif bad == "blank_skill":
        first["key_skills"] = [" "]
    elif bad == "duplicate_skills":
        first["key_skills"] = ["Cell Structure", "cell-structure"]
    elif bad == "duplicate_title":
        second["title"] = "CELLS!"
    elif bad == "unknown_prerequisite":
        second["prerequisites"] = ["Unknown"]
    elif bad == "forward_prerequisite":
        first["prerequisites"] = ["Genetics"]
    elif bad == "self_prerequisite":
        first["prerequisites"] = ["Cells"]
    elif bad == "duplicate_prerequisites":
        second["prerequisites"] = ["Cells", "CELLS!"]
    elif bad == "duplicate_phase":
        value["phases"][3] = deepcopy(value["phases"][0])
    elif bad == "phase_order":
        value["phases"].reverse()
    elif bad == "blank_title":
        first["title"] = "  "
    elif bad == "blank_description":
        first["description"] = "  "
    elif bad == "goal_length":
        value["goal"] = "x" * 256
    elif bad == "title_length":
        first["title"] = "x" * 201
    elif bad == "missing_phase":
        value["phases"].pop()
    else:
        value["level"] = "Expert"
    with pytest.raises(ValidationError):
        GeneratedRoadmapTree.model_validate(value)


def test_valid_provider_tree_retains_order_and_normalizes_whitespace():
    value = tree()
    value["phases"][0]["milestones"][0]["title"] = " Cells "
    parsed = GeneratedRoadmapTree.model_validate(value)
    assert parsed.phases[0].milestones[0].title == "Cells"
    assert parsed.phases[0].milestones[1].prerequisites == ["Cells"]


def test_invalid_constructed_provider_tree_uses_valid_offline_plan(monkeypatch):
    malformed = GeneratedRoadmapTree.model_construct(goal="Biology", level="Beginner", phases=[])

    class Provider:
        async def generate_structured(self, **kwargs):
            return malformed

    monkeypatch.setattr("app.ai.registry.get_llm_provider", lambda: Provider())
    result = asyncio.run(generate_roadmap_tree("Biology"))
    assert result.goal == "Biology"
    assert len(result.phases) == 4
    assert "Offline starter plan" in result.phases[0].milestones[0].description


@pytest.mark.parametrize("field,value", [("goal", "Astronomy"), ("level", "Advanced")])
def test_provider_cannot_change_requested_goal_or_level(monkeypatch, field, value):
    payload = tree()
    payload[field] = value

    class Provider:
        async def generate_structured(self, **kwargs):
            return GeneratedRoadmapTree.model_validate(payload)

    monkeypatch.setattr("app.ai.registry.get_llm_provider", lambda: Provider())
    result = asyncio.run(generate_roadmap_tree("Biology", "Beginner"))
    assert result.goal == "Biology"
    assert result.level == "Beginner"
    assert "Offline starter plan" in result.phases[0].milestones[0].description


def test_rephrased_goal_keeps_ai_plan_and_fallback_is_logged(monkeypatch, caplog):
    payload = tree()
    payload["goal"] = "Biology fundamentals"

    class Provider:
        async def generate_structured(self, **kwargs):
            return GeneratedRoadmapTree.model_validate(payload)

    monkeypatch.setattr("app.ai.registry.get_llm_provider", lambda: Provider())
    result = asyncio.run(generate_roadmap_tree("Learn biology", "Beginner"))
    assert result._generation_mode == "ai"
    assert result.goal == "Learn biology"

    payload["goal"] = "Astronomy"
    with caplog.at_level("WARNING", logger="app.services.roadmap"):
        result = asyncio.run(generate_roadmap_tree("Learn biology", "Beginner"))
    assert result._generation_mode == "starter"
    assert "fallback_reason=invalid_output" in caplog.text


@pytest.mark.parametrize("goal", ["x" * 255, "."])
def test_fallback_supports_all_accepted_goal_lengths_and_text(monkeypatch, goal):
    monkeypatch.setattr("app.ai.registry.get_llm_provider", lambda: None)
    result = asyncio.run(generate_roadmap_tree(goal))
    assert result.goal == goal
    assert all(len(m.title) <= 200 for phase in result.phases for m in phase.milestones)


def test_roadmap_route_rate_gate_blocks_generation(client, monkeypatch):
    registered = client.post("/api/v1/auth/register", json={
        "email": "roadmap-rate@example.com", "password": "roadmap-rate-password",
    })
    assert registered.status_code == 201

    async def unexpected_generation(*args, **kwargs):
        raise AssertionError("Rate-limited calls must not generate or persist a roadmap")

    monkeypatch.setattr("app.security.rate_limit._active", lambda: True)
    monkeypatch.setattr("app.security.rate_limit.allow_request_any", lambda *args, **kwargs: False)
    monkeypatch.setattr("app.services.roadmap.generate_roadmap_tree", unexpected_generation)
    response = client.post("/api/v1/roadmaps", json={"goal": "Biology"}, headers={
        "Authorization": "Bearer " + registered.json()["access_token"],
    })
    assert response.status_code == 429
