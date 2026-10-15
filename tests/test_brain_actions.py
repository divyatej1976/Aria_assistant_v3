from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from tests.test_audio import create_context, headers, register

from app.core.config import get_settings
from app.db.models import AuditLog, BrainAction, ConversationMessage, StudySession


@pytest.fixture
def graph_setup(client, session_factory, monkeypatch, tmp_path):
    if session_factory.kw["bind"].dialect.name != "sqlite":
        pytest.skip("SQLite graph runtime stage; PostgreSQL checkpointer is a separate rollout")
    settings = get_settings()
    monkeypatch.setattr(settings, "aria_brain_routing", True)
    monkeypatch.setattr(settings, "aria_brain_llm_routing", False)
    monkeypatch.setattr(settings, "aria_brain_checkpoint_path", str(tmp_path / "checkpoints.db"))
    from app.services.audio_storage import LocalAudioStorage

    monkeypatch.setattr("app.services.audio.get_audio_storage", lambda: LocalAudioStorage(tmp_path / "audio"))
    token = register(client, f"graph-{uuid4()}@example.com")["access_token"]
    cid = create_context(client, token)
    owner = UUID(client.get("/api/v1/auth/me", headers=headers(token)).json()["id"])
    with session_factory() as db:
        session = StudySession(owner_id=owner, context_id=UUID(cid))
        db.add(session)
        db.flush()
        sid = session.id
        db.add_all(
            [
                ConversationMessage(
                    owner_id=owner, study_session_id=sid, role="user", content="Explain stacks", position=1
                ),
                ConversationMessage(
                    owner_id=owner,
                    study_session_id=sid,
                    role="assistant",
                    content="PRIVATE_SOURCE A stack is last in, first out.",
                    position=2,
                ),
            ]
        )
        db.commit()
    return token, cid, str(sid), owner, tmp_path


def propose(client, token, sid, request_id=None):
    result = client.post(
        f"/api/v1/study/sessions/{sid}/messages",
        headers=headers(token),
        json={"content": "Make audio from this chat", "request_id": str(request_id or uuid4())},
    )
    assert result.status_code == 200, result.text
    assert result.json()["action"]["status"] == "proposed", result.text
    return result.json()["action"]["id"]


def test_graph_action_is_saved_replayable_and_checkpoints_contain_no_source(
    client, graph_setup, monkeypatch, session_factory
):
    token, cid, sid, owner, tmp_path = graph_setup
    calls = []

    class TTS:
        def generate(self, *, text):
            calls.append(text)
            return b"audio", "audio/mpeg", 4

    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: TTS())
    request_id = uuid4()
    aid = propose(client, token, sid, request_id)
    path = f"/api/v1/orchestration/actions/{aid}"
    first = client.post(path + "/run", headers=headers(token))
    assert first.status_code == 200 and first.json()["status"] == "done", first.text
    second = client.post(path + "/run", headers=headers(token))
    assert second.json()["artifact_id"] == first.json()["artifact_id"]
    assert len(calls) == 1
    retry = client.post(
        f"/api/v1/study/sessions/{sid}/messages",
        headers=headers(token),
        json={"content": "Make audio from this chat", "request_id": str(request_id)},
    )
    assert retry.json()["action"]["status"] == "done"
    assert retry.json()["action"]["id"] == aid
    messages = client.get(f"/api/v1/study/sessions/{sid}/messages", headers=headers(token)).json()
    assert messages[-1]["action"]["status"] == "done"
    assert len(client.get(f"/api/v1/audio?context_id={cid}", headers=headers(token)).json()) == 1
    import sqlite3

    with sqlite3.connect(tmp_path / "checkpoints.db") as conn:
        assert conn.execute("select count(*) from checkpoints").fetchone()[0] > 0
        for table, column in [("checkpoints", "checkpoint"), ("writes", "value")]:
            assert all(
                b"PRIVATE_SOURCE" not in bytes(row[0] or b"") for row in conn.execute(f"select {column} from {table}")
            )
    with session_factory() as db:
        assert "PRIVATE_SOURCE" not in str(
            [a.detail for a in db.scalars(select(AuditLog).where(AuditLog.agent == "langgraph"))]
        )


def test_failed_graph_retries_same_frozen_source_after_later_messages(
    client, graph_setup, monkeypatch, session_factory
):
    token, cid, sid, owner, _ = graph_setup

    class Broken:
        def generate(self, *, text):
            raise RuntimeError("private-provider-error")

    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: Broken())
    aid = propose(client, token, sid)
    path = f"/api/v1/orchestration/actions/{aid}"
    failed = client.post(path + "/run", headers=headers(token))
    assert failed.json()["status"] == "failed", failed.text
    with session_factory() as db:
        db.add(
            ConversationMessage(
                owner_id=owner, study_session_id=UUID(sid), role="assistant", content="LATER_CONTENT", position=100
            )
        )
        db.commit()

    class Good:
        def generate(self, *, text):
            assert "LATER_CONTENT" not in text
            return b"ok", "audio/mpeg", 2

    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: Good())
    retried = client.post(path + "/run", headers=headers(token))
    assert retried.json()["status"] == "done", retried.text
    assert len(client.get(f"/api/v1/audio?context_id={cid}", headers=headers(token)).json()) == 1


def test_action_ownership_cancel_and_active_claim(client, graph_setup, monkeypatch, session_factory):
    token, cid, sid, owner, _ = graph_setup
    aid = propose(client, token, sid)
    path = f"/api/v1/orchestration/actions/{aid}"
    other = register(client, f"graph-other-{uuid4()}@example.com")["access_token"]
    for suffix in ["", "/run", "/cancel"]:
        response = (
            client.get(path, headers=headers(other))
            if not suffix
            else client.post(path + suffix, headers=headers(other))
        )
        assert response.status_code == 404
    assert client.post(path + "/cancel", headers=headers(token)).json()["status"] == "cancelled"
    assert client.post(path + "/run", headers=headers(token)).json()["status"] == "cancelled"
    second = propose(client, token, sid)
    with session_factory() as db:
        action = db.get(BrainAction, UUID(second))
        action.status, action.lease_until, action.claim_id = (
            "running",
            datetime.now(UTC) + timedelta(minutes=5),
            uuid4(),
        )
        db.commit()
    path2 = f"/api/v1/orchestration/actions/{second}"
    assert client.post(path2 + "/run", headers=headers(token)).json()["status"] == "running"
    assert client.post(path2 + "/cancel", headers=headers(token)).status_code == 409
    with session_factory() as db:
        action = db.get(BrainAction, UUID(second))
        action.lease_until = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    recovered = client.get(path2, headers=headers(token)).json()
    assert recovered["status"] == "failed" and recovered["error_code"] == "worker_interrupted"
    assert client.delete(f"/api/v1/study/sessions/{sid}", headers=headers(token)).status_code == 200
    assert client.get(path2, headers=headers(token)).status_code == 404


def test_master_switch_and_intent_rules_are_safe(client, graph_setup, monkeypatch):
    import asyncio

    from app.services.brain.router import route

    token, cid, sid, owner, _ = graph_setup
    for question in [
        "Don't make audio from this chat",
        "How do I make audio from this chat?",
        "Explain audio from this conversation",
    ]:
        assert asyncio.run(route(None, owner_id=owner, context_id=UUID(cid), message=question)).capability == "answer"
    monkeypatch.setattr(get_settings(), "aria_brain_routing", False)
    assert (
        asyncio.run(route(None, owner_id=owner, context_id=UUID(cid), message="make audio from this chat")).capability
        == "answer"
    )
