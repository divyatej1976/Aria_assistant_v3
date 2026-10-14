import uuid

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "display_name": "Tutor Tester"},
    )
    assert response.status_code == 201
    return response.json()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class _DualSourceMockProvider:
    """Mock provider that mimics the dual-source structured response format."""

    async def generate_text(self, *, system: str, user: str, prompt_version=None, temperature=0.0) -> str:
        if "Study material:" in user:
            return (
                "### 📄 Information from Document: Locks\n"
                "- **Two-Phase Locking (2PL)** requires a growing phase and a shrinking phase.\n"
                "*This information is directly from your uploaded document.*\n\n"
                "### 💡 Extra Info (ARIA Enhancement)\n"
                "*(Out of document — extra information provided by ARIA)*\n"
                "In practice, Strict 2PL (S2PL) prevents cascading aborts by holding exclusive locks until commit.\n\n"
                "**Source Document:** Locks"
            )
        if "Python code" in user or "clean Python code" in user:
            return (
                "### 📚 Python Implementation\n"
                "```python\n"
                "# Linear Search Implementation\n"
                "def linear_search(arr, target):\n"
                "    for idx, val in enumerate(arr):\n"
                "        if val == target:\n"
                "            return idx\n"
                "    return -1\n"
                "```\n\n"
                "**Source:** ARIA Knowledge Base (No document attached)"
            )
        return (
            "A binary search tree is a node-based binary tree data structure with key ordering.\n\n"
            "**Source:** ARIA Knowledge Base (No document attached)"
        )

    async def generate_structured(self, *, prompt: str, schema: type, prompt_version=None):
        raise NotImplementedError


def test_tutor_answers_general_query_without_material(client: TestClient, monkeypatch) -> None:
    """Test 1: Asking questions without uploaded document yields answer and knowledge-base footer."""
    import app.services.study as study

    user = _register(client, f"tutor-gen-{uuid.uuid4().hex[:8]}@example.com")
    ctx = client.post(
        "/api/v1/contexts",
        headers=_headers(user["access_token"]),
        json={"title": "Data Structures", "description": "Trees and graphs"},
    ).json()

    session = client.post(
        "/api/v1/study/sessions",
        headers=_headers(user["access_token"]),
        json={"context_id": ctx["id"]},
    ).json()

    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: _DualSourceMockProvider())

    def unexpected_embedding_provider():
        raise AssertionError("A subject with no notes must not require embeddings")

    monkeypatch.setattr(study, "get_embedding_provider", unexpected_embedding_provider)

    res = client.post(
        f"/api/v1/study/sessions/{session['id']}/messages",
        headers=_headers(user["access_token"]),
        json={"content": "Explain what a binary search tree is."},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["fallback_used"] is False
    assert "binary search tree" in body["content"].lower()
    assert "**Source:** ARIA Knowledge Base (No document attached)" in body["content"]


def test_no_notes_without_key_explains_configuration(client: TestClient, monkeypatch) -> None:
    import app.services.study as study

    user = _register(client, f"tutor-no-key-{uuid.uuid4().hex[:8]}@example.com")
    headers = _headers(user["access_token"])
    ctx = client.post(
        "/api/v1/contexts", headers=headers,
        json={"title": "Algorithms", "description": ""},
    ).json()
    session = client.post(
        "/api/v1/study/sessions", headers=headers, json={"context_id": ctx["id"]},
    ).json()
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: None)
    response = client.post(
        f"/api/v1/study/sessions/{session['id']}/messages", headers=headers,
        json={"content": "Explain binary search."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fallback_used"] is True
    assert body["sources"] == []
    assert "without uploaded notes" in body["content"]
    assert "Account settings" in body["content"]
    assert "not find enough relevant information" not in body["content"]


def test_tutor_dual_source_grounding_with_uploaded_document(client: TestClient, monkeypatch) -> None:
    """Test 2: Asking question with uploaded material generates dual-source sections and source footer."""
    import app.services.study as study

    user = _register(client, f"tutor-doc-{uuid.uuid4().hex[:8]}@example.com")
    ctx = client.post(
        "/api/v1/contexts",
        headers=_headers(user["access_token"]),
        json={"title": "Databases", "description": "Concurrency control"},
    ).json()

    # Upload material
    upload = client.post(
        "/api/v1/resources/text",
        headers=_headers(user["access_token"]),
        json={
            "context_id": ctx["id"],
            "title": "Locks",
            "text": "Two-phase locking has a growing phase and a shrinking phase. Locks are acquired during growth.",
        },
    )
    assert upload.status_code == 201

    session = client.post(
        "/api/v1/study/sessions",
        headers=_headers(user["access_token"]),
        json={"context_id": ctx["id"]},
    ).json()

    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: _DualSourceMockProvider())

    res = client.post(
        f"/api/v1/study/sessions/{session['id']}/messages",
        headers=_headers(user["access_token"]),
        json={"content": "How does two-phase locking work?"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["fallback_used"] is False
    assert body["sources"]
    assert "### 📄 Information from Document" in body["content"]
    assert "### 💡 Extra Info (ARIA Enhancement)" in body["content"]
    assert "**Source Document:** Locks" in body["content"]


def test_tutor_self_loop_pattern_adaptation(client: TestClient, monkeypatch) -> None:
    """Test 3: Tutor adapts to user pattern (e.g. requesting code) in multi-turn conversation."""
    import app.services.study as study

    user = _register(client, f"tutor-loop-{uuid.uuid4().hex[:8]}@example.com")
    ctx = client.post(
        "/api/v1/contexts",
        headers=_headers(user["access_token"]),
        json={"title": "Algorithms", "description": "Search algorithms"},
    ).json()

    session = client.post(
        "/api/v1/study/sessions",
        headers=_headers(user["access_token"]),
        json={"context_id": ctx["id"]},
    ).json()

    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: _DualSourceMockProvider())

    # Turn 1: Establish code preference
    t1 = client.post(
        f"/api/v1/study/sessions/{session['id']}/messages",
        headers=_headers(user["access_token"]),
        json={"content": "I learn best with clean Python code snippets. Please explain things with Python code."},
    )
    assert t1.status_code == 200

    # Turn 2: Ask new question
    t2 = client.post(
        f"/api/v1/study/sessions/{session['id']}/messages",
        headers=_headers(user["access_token"]),
        json={"content": "Explain how linear search works."},
    )
    assert t2.status_code == 200
    body2 = t2.json()
    assert "```python" in body2["content"]
    assert "linear_search" in body2["content"]
