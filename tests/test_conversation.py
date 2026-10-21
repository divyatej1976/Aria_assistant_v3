"""Phase 13 conversation ordering: unique positions and concurrency retry."""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

import app.services.study as study
from app.db.models import ConversationMessage, StudySession

MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time. "
    "A precedence graph detects cycles that indicate non-serializable schedules."
)


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-9", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _learner_with_session(
    client: TestClient, email: str
) -> tuple[str, str, str]:
    session = register(client, email)
    token = session["access_token"]
    context = client.post(
        "/api/v1/contexts", headers=headers(token), json={"title": "DBMS"}
    ).json()
    client.post(
        "/api/v1/resources/text",
        headers=headers(token),
        json={"context_id": context["id"], "title": "Locks", "text": MATERIAL},
    )
    study_session = client.post(
        "/api/v1/study/sessions", headers=headers(token), json={"context_id": context["id"]}
    ).json()
    return token, study_session["id"], session["learner_id"]


def test_positions_are_monotonic_and_unique_across_turns(
    client: TestClient, engine
) -> None:
    token, session_id, _ = _learner_with_session(client, "conv-pos@example.com")
    for question in ("What is locking?", "What is a precedence graph?"):
        response = client.post(
            f"/api/v1/study/sessions/{session_id}/messages",
            headers=headers(token),
            json={"content": question},
        )
        assert response.status_code == 200

    messages = client.get(
        f"/api/v1/study/sessions/{session_id}/messages", headers=headers(token)
    ).json()
    assert len(messages) == 4
    assert [message["role"] for message in messages] == [
        "user", "assistant", "user", "assistant",
    ]

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db: Session = factory()
    try:
        positions = [
            row
            for (row,) in db.execute(
                select(ConversationMessage.position).where(
                    ConversationMessage.study_session_id == UUID(session_id)
                )
            ).all()
        ]
    finally:
        db.close()
    assert sorted(positions) == [1, 2, 3, 4]


def test_persist_retries_on_position_collision(
    client: TestClient, engine, monkeypatch
) -> None:
    token, session_id, learner_id = _learner_with_session(client, "conv-race@example.com")
    client.post(
        f"/api/v1/study/sessions/{session_id}/messages",
        headers=headers(token),
        json={"content": "First turn"},
    )

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    real_next = study._next_position
    calls = {"count": 0}

    def stale_first(db, *, owner_id, session_id):
        calls["count"] += 1
        if calls["count"] == 1:
            return 2
        return real_next(db, owner_id=owner_id, session_id=session_id)

    monkeypatch.setattr(study, "_next_position", stale_first)

    db: Session = factory()
    try:
        session_obj = db.get(StudySession, UUID(session_id))
        study.persist_conversation_turn(
            db,
            owner_id=UUID(learner_id),
            session=session_obj,
            user_content="Second turn",
            assistant_content="Answer",
            assistant_refs=[],
        )
    finally:
        db.close()

    assert calls["count"] >= 2

    db = factory()
    try:
        positions = [
            row
            for (row,) in db.execute(
                select(ConversationMessage.position).where(
                    ConversationMessage.study_session_id == UUID(session_id)
                )
            ).all()
        ]
    finally:
        db.close()
    assert sorted(positions) == [1, 2, 3, 4]
