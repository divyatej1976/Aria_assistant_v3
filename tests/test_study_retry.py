import asyncio
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select
from tests.test_resources_study import create_context, headers, register

from app.db.models import ConversationMessage, IdempotencyKey
from app.services.study import StudyResult


def setup_chat(client):
    token = register(client, "retry@example.com")["access_token"]
    context = create_context(client, token)
    session = client.post("/api/v1/study/sessions", headers=headers(token), json={"context_id": context}).json()["id"]
    return token, session


def test_reply_retry_replays_one_turn_after_request_key_cleanup(client, session_factory, monkeypatch):
    calls = []
    async def answer(*args, **kwargs):
        calls.append(kwargs["question"])
        return StudyResult("An answer that can be replayed safely.", [], False)
    monkeypatch.setattr("app.services.study_requests.answer_question", answer)
    token, session = setup_chat(client)
    url = f"/api/v1/study/sessions/{session}/messages"
    body = {"content": "Explain functions", "request_id": str(uuid4())}
    first = client.post(url, headers=headers(token), json=body)
    assert first.status_code == 200, first.text
    assert client.post(url, headers=headers(token), json=body).json() == first.json()
    with session_factory() as db:
        db.execute(delete(IdempotencyKey))
        db.commit()
    assert client.post(url, headers=headers(token), json=body).json() == first.json()
    assert client.post(url, headers=headers(token), json={**body, "content": "Different question"}).status_code == 409
    stranger = register(client, "retry-stranger@example.com")["access_token"]
    assert client.post(url, headers=headers(stranger), json=body).status_code == 404
    assert calls == ["Explain functions"]
    with session_factory() as db:
        messages = list(db.scalars(select(ConversationMessage).where(ConversationMessage.study_session_id == UUID(session))))
        assert len(messages) == 2


def test_failed_reply_can_retry_the_same_request(client, session_factory, monkeypatch):
    calls = []
    async def answer(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("Synthetic transport failure")
        return StudyResult("Recovered answer.", [], False)
    monkeypatch.setattr("app.services.study_requests.answer_question", answer)
    token, session = setup_chat(client)
    body = {"content": "Explain functions", "request_id": str(uuid4())}
    # Verify service-level failure releases the reservation before HTTP recovery.
    from app.db.models import StudySession
    from app.services.study_requests import answer_and_save
    with session_factory() as db:
        stored = db.get(StudySession, UUID(session))
        with pytest.raises(RuntimeError):
            asyncio.run(answer_and_save(db, owner_id=stored.owner_id, session=stored,
                                       content=body["content"], request_id=UUID(body["request_id"])))
    response = client.post(f"/api/v1/study/sessions/{session}/messages", headers=headers(token), json=body)
    assert response.status_code == 200, response.text
    assert response.json()["content"] == "Recovered answer."


def test_concurrent_reply_retry_dispatches_once(client, session_factory, engine, monkeypatch):
    if engine.dialect.name != "postgresql":
        pytest.skip("Independent PostgreSQL transactions required")
    assert_concurrent_reply_dispatches_once(client, session_factory, monkeypatch)


def test_concurrent_reply_retry_on_file_sqlite(client, tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker
    from app.db.base import Base
    from app.db.dependencies import get_db
    from app.main import app

    engine = create_engine(f"sqlite:///{(tmp_path / 'reply-retry.db').as_posix()}",
                           connect_args={"check_same_thread": False, "timeout": 10})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    original = app.dependency_overrides[get_db]
    def isolated_db():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = isolated_db
    try:
        assert_concurrent_reply_dispatches_once(client, factory, monkeypatch)
    finally:
        app.dependency_overrides[get_db] = original
        engine.dispose()


def assert_concurrent_reply_dispatches_once(client, session_factory, monkeypatch):
    from threading import Event
    calls = []
    started, release = Event(), Event()
    async def answer(*args, **kwargs):
        calls.append(1)
        started.set()
        while not release.is_set():
            await asyncio.sleep(0.01)
        return StudyResult("One answer.", [], False)
    monkeypatch.setattr("app.services.study_requests.answer_question", answer)
    token, session = setup_chat(client)
    body = {"content": "Explain functions", "request_id": str(uuid4())}
    def send():
        return client.post(f"/api/v1/study/sessions/{session}/messages", headers=headers(token), json=body)
    with ThreadPoolExecutor(max_workers=1) as workers:
        first = workers.submit(send)
        try:
            assert started.wait(timeout=10)
            assert send().status_code == 409
        finally:
            release.set()
        assert first.result(timeout=10).status_code == 200
    assert len(calls) == 1
    with session_factory() as db:
        assert len(list(db.scalars(select(ConversationMessage)))) == 2
