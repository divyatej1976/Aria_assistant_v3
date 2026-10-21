"""A file attached in one chat is used only by that chat, like Claude or ChatGPT."""

import asyncio
import uuid
from uuid import UUID

from fastapi.testclient import TestClient

from app.services.resource_ingestion import create_text_resource

SECRET = "The zorblax protocol rotates keys every forty seconds."


class _CapturingProvider:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate_text(self, *, system: str, user: str, prompt_version=None, temperature=0.0) -> str:
        self.prompts.append(user)
        return "Here is what I know."

    async def generate_structured(self, *, prompt: str, schema: type, prompt_version=None):
        raise NotImplementedError


def _learner(client: TestClient) -> tuple[dict, str, str, str]:
    auth = client.post(
        "/api/v1/auth/register",
        json={"email": f"attach-{uuid.uuid4().hex[:8]}@example.com", "password": "correct-horse-9",
              "display_name": "Attach Tester"},
    ).json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    ctx = client.post("/api/v1/contexts", headers=headers, json={"title": "Security"}).json()
    first = client.post("/api/v1/study/sessions", headers=headers, json={"context_id": ctx["id"]}).json()
    second = client.post("/api/v1/study/sessions", headers=headers, json={"context_id": ctx["id"]}).json()
    return headers, ctx["id"], first["id"], second["id"]


def _attach(session_factory, client: TestClient, headers: dict, context_id: str, session_id: str | None) -> str:
    owner = UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])
    with session_factory() as db:
        resource = asyncio.run(create_text_resource(
            db, owner_id=owner, context_id=UUID(context_id), title="Zorblax notes", text=SECRET,
            study_session_id=UUID(session_id) if session_id else None,
        ))
        return str(resource.id)


def _ask(client: TestClient, headers: dict, session_id: str) -> None:
    res = client.post(f"/api/v1/study/sessions/{session_id}/messages", headers=headers,
                      json={"content": "How does the zorblax protocol rotate keys?"})
    assert res.status_code == 200, res.text


def test_chat_file_is_used_only_in_its_own_chat(client: TestClient, session_factory, monkeypatch) -> None:
    import app.services.study as study

    headers, context_id, first, second = _learner(client)
    _attach(session_factory, client, headers, context_id, first)
    provider = _CapturingProvider()
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: provider)

    _ask(client, headers, first)
    _ask(client, headers, second)

    assert "zorblax protocol rotates keys" in provider.prompts[0]
    assert "zorblax protocol rotates keys" not in provider.prompts[1]


def test_library_lists_exclude_chat_files_until_shared(client: TestClient, session_factory, monkeypatch) -> None:
    import app.services.study as study

    headers, context_id, first, second = _learner(client)
    resource_id = _attach(session_factory, client, headers, context_id, first)

    library = client.get(f"/api/v1/resources?context_id={context_id}", headers=headers).json()
    in_chat = client.get(f"/api/v1/resources?context_id={context_id}&session_id={first}", headers=headers).json()
    assert library == []
    assert [item["id"] for item in in_chat] == [resource_id]
    assert in_chat[0]["session_id"] == first

    shared = client.post(f"/api/v1/resources/{resource_id}/library", headers=headers)
    assert shared.status_code == 200 and shared.json()["session_id"] is None
    provider = _CapturingProvider()
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: provider)
    _ask(client, headers, second)
    assert "zorblax protocol rotates keys" in provider.prompts[0]


def test_deleting_a_chat_deletes_its_files_but_not_the_library(client: TestClient, session_factory) -> None:
    headers, context_id, first, _second = _learner(client)
    chat_file = _attach(session_factory, client, headers, context_id, first)
    library_file = _attach(session_factory, client, headers, context_id, None)

    assert client.delete(f"/api/v1/study/sessions/{first}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/resources/{chat_file}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/resources/{library_file}", headers=headers).status_code == 200


def test_upload_rejects_a_chat_from_another_subject(client: TestClient) -> None:
    headers, context_id, _first, _second = _learner(client)
    other = client.post("/api/v1/contexts", headers=headers, json={"title": "Other"}).json()
    foreign = client.post("/api/v1/study/sessions", headers=headers, json={"context_id": other["id"]}).json()
    res = client.post(
        f"/api/v1/resources/image?context_id={context_id}&session_id={foreign['id']}",
        headers={**headers, "Content-Type": "image/png"}, content=b"\x89PNG\r\n\x1a\n",
    )
    assert res.status_code == 404


def test_summarize_this_document_sends_the_attached_file(client: TestClient, session_factory, monkeypatch) -> None:
    """'Summarize this' shares no words with the file; the attachment must still reach the tutor."""
    import app.services.study as study

    headers, context_id, first, second = _learner(client)
    _attach(session_factory, client, headers, context_id, first)
    provider = _CapturingProvider()
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: provider)

    for question in ("Summarize this document", "Can you explain it simply?"):
        res = client.post(f"/api/v1/study/sessions/{first}/messages", headers=headers, json={"content": question})
        assert res.status_code == 200, res.text
    assert all("zorblax protocol rotates keys" in prompt for prompt in provider.prompts)
    # A chat without the file still doesn't see it.
    client.post(f"/api/v1/study/sessions/{second}/messages", headers=headers, json={"content": "Summarize this document"})
    assert "zorblax protocol rotates keys" not in provider.prompts[-1]


def test_chats_get_short_titles_after_the_first_reply(client: TestClient, monkeypatch) -> None:
    """Like Claude's Recents: a few words, not the whole first question."""
    import app.ai.registry as registry
    import app.services.study as study
    from app.services.study_requests import clean_title

    class _Namer(_CapturingProvider):
        async def generate_text(self, *, system, user, prompt_version=None, temperature=0.0):
            return '"Zorblax Key Rotation."' if prompt_version == "chat_title:1" else await super().generate_text(
                system=system, user=user)

    provider = _Namer()
    monkeypatch.setattr(study, "get_llm_provider_for_owner", lambda db, owner_id: provider)
    monkeypatch.setattr(registry, "get_llm_provider_for_owner", lambda db, owner_id: provider)
    headers, context_id, first, _ = _learner(client)
    _ask(client, headers, first)
    listed = client.get(f"/api/v1/study/sessions?context_id={context_id}", headers=headers).json()
    assert next(s for s in listed if s["id"] == first)["title"] == "Zorblax Key Rotation"
    assert clean_title("This is far too long to be a chat title at all really") is None


def test_chat_titles_fall_back_to_the_topic_not_the_wording() -> None:
    from app.services.study import topic_title

    assert topic_title("hi explain me about agent harness") == "Agent Harness"
    assert topic_title("hey aria, how does two-phase locking work?") == "Two-phase Locking"
    assert topic_title("can you explain the difference between 3NF and BCNF in detail") == "Difference between 3NF and BCNF"
    assert topic_title("I want to learn about Kubernetes networking") == "Kubernetes Networking"
