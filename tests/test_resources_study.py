from fastapi.testclient import TestClient

from app.services.study import cosine_similarity, lexical_score


def test_cosine_similarity_unit() -> None:
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert abs(cosine_similarity([1.0, 2.0], [2.0, 4.0]) - 1.0) < 1e-9


def test_lexical_score_filters_stopwords() -> None:
    query = {"locking", "release", "banana"}
    assert lexical_score(query, "locking and release of the banana") == 1.0
    assert lexical_score(query, "the and of are stopwords only") == 0.0


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-9", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_context(client: TestClient, token: str, title: str = "DBMS") -> str:
    response = client.post(
        "/api/v1/contexts",
        headers=headers(token),
        json={"title": title, "description": "Study material"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def make_pdf_bytes(text: str) -> bytes:
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def upload_pdf(
    client: TestClient,
    token: str,
    context_id: str,
    content: bytes,
    title: str = "Notes",
) -> object:
    return client.post(
        f"/api/v1/resources/pdf?context_id={context_id}&title={title}",
        headers={**headers(token), "Content-Type": "application/pdf"},
        content=content,
    )


def test_text_resource_becomes_ready(client: TestClient) -> None:
    session = register(client, "resources@example.com")
    context_id = create_context(client, session["access_token"])
    response = client.post(
        "/api/v1/resources/text",
        headers=headers(session["access_token"]),
        json={
            "context_id": context_id,
            "title": "Serializability",
            "text": "Transactions are serializable when concurrent schedules are equivalent "
            "to some serial schedule. Two-phase locking and conflict equivalence are used "
            "to reason about correctness.",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["processing_status"] == "READY"
    assert body["resource_type"] == "TEXT"
    assert body["chunk_count"] >= 1
    assert body["error_detail"] is None
    assert "created_at" in body


def test_pdf_resource_becomes_ready(client: TestClient) -> None:
    session = register(client, "pdf@example.com")
    context_id = create_context(client, session["access_token"])
    pdf_bytes = make_pdf_bytes("Conflict serializability is tested with precedence graphs.")
    response = upload_pdf(client, session["access_token"], context_id, pdf_bytes)
    assert response.status_code == 201
    body = response.json()
    assert body["processing_status"] == "READY"
    assert body["resource_type"] == "PDF"
    assert body["chunk_count"] >= 1


def test_pdf_extraction_runs_off_event_loop(
    client: TestClient, monkeypatch
) -> None:
    """OCR/PDF extraction must go through the worker-thread offload, never
    inline on the event loop where it would stall concurrent requests."""
    import anyio.to_thread

    calls: list[str] = []
    real_run_sync = anyio.to_thread.run_sync

    async def spy(func, *args, **kwargs):
        calls.append(getattr(func, "__name__", repr(func)))
        return await real_run_sync(func, *args, **kwargs)

    monkeypatch.setattr(anyio.to_thread, "run_sync", spy)
    session = register(client, "offloop@example.com")
    context_id = create_context(client, session["access_token"])
    pdf_bytes = make_pdf_bytes(
        "Two-phase locking coordinates concurrent database transactions safely."
    )
    response = upload_pdf(client, session["access_token"], context_id, pdf_bytes)
    assert response.status_code == 201
    assert response.json()["processing_status"] == "READY"
    assert "extract_pdf_text" in calls


def test_unsupported_upload_is_marked_unsupported(client: TestClient) -> None:
    session = register(client, "unsupported@example.com")
    context_id = create_context(client, session["access_token"])
    response = upload_pdf(
        client, session["access_token"], context_id, b"this is not a pdf at all"
    )
    assert response.status_code == 201
    body = response.json()
    assert body["processing_status"] == "UNSUPPORTED"
    assert body["error_detail"] == "Unsupported file type; upload a PDF"
    assert body["chunk_count"] == 0


def test_garbage_pdf_fails_then_replace_recovers(client: TestClient) -> None:
    session = register(client, "garbage@example.com")
    context_id = create_context(client, session["access_token"])
    bad = upload_pdf(
        client,
        session["access_token"],
        context_id,
        b"%PDF-1.7\nthis is not a real pdf body",
    )
    assert bad.status_code == 201
    assert bad.json()["processing_status"] == "FAILED"
    assert bad.json()["error_detail"] == "The uploaded PDF could not be read"

    resource_id = bad.json()["id"]
    replacement = upload_pdf(
        client,
        session["access_token"],
        context_id,
        make_pdf_bytes("A fixed document with real content."),
        title="Fixed",
    )
    assert replacement.status_code == 201
    replacement_id = replacement.json()["id"]
    assert replacement_id != resource_id

    replaced = client.put(
        f"/api/v1/resources/{resource_id}/pdf?title=Fixed",
        headers={**headers(session["access_token"]), "Content-Type": "application/pdf"},
        content=make_pdf_bytes("A fixed document with real content."),
    )
    assert replaced.status_code == 200
    body = replaced.json()
    assert body["processing_status"] == "READY"
    assert body["chunk_count"] >= 1


def test_retry_does_not_duplicate_chunks(client: TestClient) -> None:
    session = register(client, "retry@example.com")
    context_id = create_context(client, session["access_token"])
    created = client.post(
        "/api/v1/resources/text",
        headers=headers(session["access_token"]),
        json={
            "context_id": context_id,
            "title": "Indexes",
            "text": "A B-tree index speeds up equality and range lookups at the cost of "
            "extra write overhead and storage.",
        },
    ).json()
    first_count = created["chunk_count"]
    assert first_count >= 1

    retried = client.post(
        f"/api/v1/resources/{created['id']}/process",
        headers=headers(session["access_token"]),
    )
    assert retried.status_code == 200
    assert retried.json()["chunk_count"] == first_count


def test_replace_text_resource_reprocesses(client: TestClient) -> None:
    session = register(client, "replace@example.com")
    context_id = create_context(client, session["access_token"])
    created = client.post(
        "/api/v1/resources/text",
        headers=headers(session["access_token"]),
        json={"context_id": context_id, "title": "Old", "text": "First version of the notes."},
    ).json()
    replaced = client.put(
        f"/api/v1/resources/{created['id']}/text",
        headers=headers(session["access_token"]),
        json={"title": "New", "text": "Second version with much more detailed content here."},
    )
    assert replaced.status_code == 200
    body = replaced.json()
    assert body["title"] == "New"
    assert body["processing_status"] == "READY"
    assert body["chunk_count"] >= 1


def test_delete_resource_removes_it(client: TestClient) -> None:
    session = register(client, "delete@example.com")
    context_id = create_context(client, session["access_token"])
    created = client.post(
        "/api/v1/resources/text",
        headers=headers(session["access_token"]),
        json={"context_id": context_id, "title": "Temp", "text": "Will be removed soon."},
    ).json()
    deleted = client.delete(
        f"/api/v1/resources/{created['id']}", headers=headers(session["access_token"])
    )
    assert deleted.status_code == 200
    detail = client.get(
        f"/api/v1/resources/{created['id']}", headers=headers(session["access_token"])
    )
    assert detail.status_code == 404
    listed = client.get(
        f"/api/v1/resources?context_id={context_id}", headers=headers(session["access_token"])
    )
    assert listed.json() == []


def test_resources_are_isolated_between_learners(client: TestClient) -> None:
    first = register(client, "first-res@example.com")
    second = register(client, "second-res@example.com")
    first_context = create_context(client, first["access_token"])
    second_context = create_context(client, second["access_token"])
    created = client.post(
        "/api/v1/resources/text",
        headers=headers(first["access_token"]),
        json={
            "context_id": first_context,
            "title": "Private",
            "text": "Private material belonging to the first learner.",
        },
    ).json()

    stolen = client.get(
        f"/api/v1/resources/{created['id']}", headers=headers(second["access_token"])
    )
    assert stolen.status_code == 404
    deleted = client.delete(
        f"/api/v1/resources/{created['id']}", headers=headers(second["access_token"])
    )
    assert deleted.status_code == 404
    listed_second = client.get(
        f"/api/v1/resources?context_id={second_context}",
        headers=headers(second["access_token"]),
    )
    assert listed_second.json() == []
    listed_first = client.get(
        f"/api/v1/resources?context_id={first_context}", headers=headers(first["access_token"])
    )
    assert len(listed_first.json()) == 1


def test_resource_chunks_endpoint(client: TestClient) -> None:
    session = register(client, "chunks@example.com")
    context_id = create_context(client, session["access_token"])
    created = client.post(
        "/api/v1/resources/text",
        headers=headers(session["access_token"]),
        json={
            "context_id": context_id,
            "title": "Chunked",
            "text": (
                "First sentence about serializability. "
                "Second sentence about precedence graphs."
            ),
        },
    ).json()
    response = client.get(
        f"/api/v1/resources/{created['id']}/chunks",
        headers=headers(session["access_token"]),
    )
    assert response.status_code == 200
    chunks = response.json()
    assert len(chunks) >= 1
    assert chunks[0]["content"]


def test_study_answers_grounded_in_material(client: TestClient) -> None:
    session = register(client, "study@example.com")
    context_id = create_context(client, session["access_token"])
    client.post(
        "/api/v1/resources/text",
        headers=headers(session["access_token"]),
        json={
            "context_id": context_id,
            "title": "Locks",
            "text": "Two-phase locking requires a growth phase and a shrink phase. "
            "Strict two-phase locking releases locks only at commit time.",
        },
    )
    created = client.post(
        "/api/v1/study/sessions",
        headers=headers(session["access_token"]),
        json={"context_id": context_id},
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    answer = client.post(
        f"/api/v1/study/sessions/{session_id}/messages",
        headers=headers(session["access_token"]),
        json={"content": "When does strict two-phase locking release its locks?"},
    )
    assert answer.status_code == 200
    body = answer.json()
    assert body["content"]
    assert isinstance(body["sources"], list)

    history = client.get(
        f"/api/v1/study/sessions/{session_id}/messages",
        headers=headers(session["access_token"]),
    )
    assert history.status_code == 200
    messages = history.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["sources"][0]["resource_id"]


def test_study_reports_missing_key_when_material_is_irrelevant(client: TestClient) -> None:
    session = register(client, "insufficient@example.com")
    context_id = create_context(client, session["access_token"])
    client.post(
        "/api/v1/resources/text",
        headers=headers(session["access_token"]),
        json={
            "context_id": context_id,
            "title": "Locks",
            "text": "Two-phase locking has a growth phase and a shrink phase.",
        },
    )
    created = client.post(
        "/api/v1/study/sessions",
        headers=headers(session["access_token"]),
        json={"context_id": context_id},
    ).json()
    answer = client.post(
        f"/api/v1/study/sessions/{created['id']}/messages",
        headers=headers(session["access_token"]),
        json={"content": "Explain quantum chromodynamics and the banana diet"},
    )
    assert answer.status_code == 200
    body = answer.json()
    assert body["fallback_used"] is True
    assert "no usable LLM API key" in body["content"]
    assert "Account settings" in body["content"]


def test_study_sessions_are_context_scoped(client: TestClient) -> None:
    session = register(client, "scope@example.com")
    context_id = create_context(client, session["access_token"])
    client.post(
        "/api/v1/study/sessions",
        headers=headers(session["access_token"]),
        json={"context_id": context_id},
    )
    listed = client.get(
        f"/api/v1/study/sessions?context_id={context_id}",
        headers=headers(session["access_token"]),
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    other_context = create_context(client, session["access_token"], title="Other")
    other_listed = client.get(
        f"/api/v1/study/sessions?context_id={other_context}",
        headers=headers(session["access_token"]),
    )
    assert other_listed.json() == []


def test_session_list_describes_what_was_covered(client: TestClient) -> None:
    session = register(client, "summary@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    empty = client.post(
        "/api/v1/study/sessions", headers=headers(token), json={"context_id": context_id}
    ).json()
    talked = client.post(
        "/api/v1/study/sessions", headers=headers(token), json={"context_id": context_id}
    ).json()
    question = "When does **strict** two-phase locking release its locks in a transaction?"
    assert client.post(
        f"/api/v1/study/sessions/{talked['id']}/messages",
        headers=headers(token),
        json={"content": question},
    ).status_code == 200

    listed = {
        item["id"]: item
        for item in client.get(
            f"/api/v1/study/sessions?context_id={context_id}", headers=headers(token)
        ).json()
    }
    covered = listed[talked["id"]]
    assert covered["message_count"] == 2
    assert covered["title"] == "Strict Two-phase Locking"  # the topic, not the question wording
    assert len(covered["title"]) <= 61 and "*" not in covered["title"]
    assert covered["preview"]
    assert covered["last_message_at"] is not None
    blank = listed[empty["id"]]
    assert blank["message_count"] == 0
    assert blank["title"] is None and blank["preview"] is None


def test_pdf_upload_over_size_limit_is_rejected(client: TestClient) -> None:
    from app.api.routes.resources import MAX_UPLOAD_BYTES

    session = register(client, "oversize@example.com")
    context_id = create_context(client, session["access_token"])
    response = upload_pdf(
        client,
        session["access_token"],
        context_id,
        content=b"%PDF" + b"\x00" * (MAX_UPLOAD_BYTES + 1),
    )
    assert response.status_code == 413


def test_material_attaches_only_when_it_shares_the_subject():
    from app.services.study import _on_topic, content_terms

    sampling = "Stratified sampling keeps each class proportion; cluster sampling picks whole data groups."
    terms = lambda q: {t for t in content_terms(q) if len(t) > 2}  # noqa: E731
    assert not _on_topic(terms("Quiz me with 3 questions on data structures"), sampling)
    assert not _on_topic(terms("What is the second question"), sampling)
    assert _on_topic(terms("Explain stratified sampling"), sampling)
    revision = ("Help me revise what I got wrong. 1. How many majority records does random undersampling "
                "remove? 2. Why does stratified sampling keep class proportion? 3. What does SMOTE interpolate? "
                "4. When is cluster sampling cheap? 5. What causes sampling bias in online surveys?")
    assert _on_topic(terms(revision), sampling)
