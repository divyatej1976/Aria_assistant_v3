from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Note, RevisionItem
from app.services.notes import build_note_pdf, due_notes

MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time. "
    "A precedence graph detects cycles that indicate non-serializable schedules. "
    "Conflict serializability is a subset of view serializability for most schedules. "
    "Deadlock detection requires waiting for a cycle in the resource wait-for graph."
)


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_context(client: TestClient, token: str) -> str:
    response = client.post(
        "/api/v1/contexts",
        headers=headers(token),
        json={"title": "DBMS", "description": "Notes tests"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def add_material(client: TestClient, token: str, context_id: str) -> None:
    response = client.post(
        "/api/v1/resources/text",
        headers=headers(token),
        json={"context_id": context_id, "title": "Locks", "text": MATERIAL},
    )
    assert response.status_code == 201


def create_note(client: TestClient, token: str, context_id: str, title: str = "My note") -> dict:
    response = client.post(
        "/api/v1/notes",
        headers=headers(token),
        json={"context_id": context_id, "title": title, "body": "Serializability matters."},
    )
    assert response.status_code == 201
    return response.json()


def test_notes_crud_and_isolation(client: TestClient) -> None:
    first = register(client, "notes-a@example.com")
    second = register(client, "notes-b@example.com")
    context_id = create_context(client, first["access_token"])
    note = create_note(client, first["access_token"], context_id)
    note_id = note["id"]
    assert note["state"] == "NEW"
    assert note["interval_days"] == 1
    assert note["next_review_at"] is not None

    listed = client.get(
        f"/api/v1/notes?context_id={context_id}", headers=headers(first["access_token"])
    )
    assert len(listed.json()) == 1

    updated = client.put(
        f"/api/v1/notes/{note_id}",
        headers=headers(first["access_token"]),
        json={"title": "Edited note", "body": "Updated body."},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Edited note"

    isolated = client.get(
        f"/api/v1/notes?context_id={context_id}", headers=headers(second["access_token"])
    )
    assert isolated.status_code == 404

    detail = client.get(
        f"/api/v1/notes/{note_id}", headers=headers(second["access_token"])
    )
    assert detail.status_code == 404

    deleted = client.delete(f"/api/v1/notes/{note_id}", headers=headers(first["access_token"]))
    assert deleted.status_code == 200
    gone = client.get(f"/api/v1/notes/{note_id}", headers=headers(first["access_token"]))
    assert gone.status_code == 404


def test_generate_note_fallback(client: TestClient) -> None:
    session = register(client, "notes-gen@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    add_material(client, token, context_id)
    generated = client.post(
        "/api/v1/notes/generate",
        headers=headers(token),
        json={"context_id": context_id},
    )
    assert generated.status_code == 201
    body = generated.json()
    assert body["title"]
    assert body["body"]
    assert body["context_id"] == context_id


def test_review_advances_schedule(client: TestClient) -> None:
    session = register(client, "notes-review@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    note = create_note(client, token, context_id)

    good = client.post(
        f"/api/v1/notes/{note['id']}/review",
        headers=headers(token),
        json={"outcome": "good"},
    )
    assert good.status_code == 200
    assert good.json()["interval_days"] == 3
    assert good.json()["state"] == "LEARNING"
    assert good.json()["last_outcome"] == "GOOD"

    again = client.post(
        f"/api/v1/notes/{note['id']}/review",
        headers=headers(token),
        json={"outcome": "again"},
    )
    assert again.json()["interval_days"] == 1
    assert again.json()["state"] == "REVIEWING"


def test_due_queue(client: TestClient) -> None:
    session = register(client, "notes-due@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    create_note(client, token, context_id)

    due = client.get(
        f"/api/v1/notes/due?context_id={context_id}", headers=headers(token)
    )
    assert due.status_code == 200
    assert due.json() == []

    due_again = client.get(
        f"/api/v1/notes/due?context_id={context_id}", headers=headers(token)
    )
    assert [item["id"] for item in due_again.json()] == []


def test_due_notes_service() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_factory() as db:
        owner_id = uuid4()
        context_id = uuid4()
        overdue = Note(
            id=uuid4(),
            owner_id=owner_id,
            context_id=context_id,
            title="Overdue",
            body="body",
        )
        future = Note(
            id=uuid4(),
            owner_id=owner_id,
            context_id=context_id,
            title="Future",
            body="body",
        )
        db.add_all([overdue, future])
        db.flush()
        now = datetime.now(UTC)
        db.add_all(
            [
                RevisionItem(
                    owner_id=owner_id,
                    note_id=overdue.id,
                    state="NEW",
                    interval_days=1,
                    next_review_at=now - timedelta(days=1),
                ),
                RevisionItem(
                    owner_id=owner_id,
                    note_id=future.id,
                    state="NEW",
                    interval_days=1,
                    next_review_at=now + timedelta(days=1),
                ),
            ]
        )
        db.commit()
        result = due_notes(db, owner_id=owner_id, context_id=context_id)
    engine.dispose()
    assert [note.title for note in result] == ["Overdue"]


def test_note_pdf_download(client: TestClient) -> None:
    session = register(client, "notes-pdf@example.com")
    token = session["access_token"]
    context_id = create_context(client, token)
    note = create_note(client, token, context_id, title="Serializability のメモ")
    response = client.get(f"/api/v1/notes/{note['id']}/download", headers=headers(token))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content[:5] == b"%PDF-"


def test_note_pdf_builder_handles_unicode() -> None:
    note = Note(
        id=uuid4(),
        owner_id=uuid4(),
        context_id=uuid4(),
        title="日本語 テスト",
        body="直列化可能性についてのメモ。\n\n別段落。",
        source_refs=[{"title": "DBMS 教材"}],
    )
    content = build_note_pdf(note)
    assert content[:5] == b"%PDF-"
