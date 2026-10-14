import asyncio
from uuid import uuid4

import pytest
from tests.test_brain_snapshot import learner_context

from app.core.errors import ValidationError
from app.db.models import ConversationMessage, StudySession
from app.services.brain.capabilities import CAPABILITIES, execute_capability, get_capability
from app.services.orchestration import AGENTS


def test_registry_adapts_legacy_agents_and_rejects_unknown_or_extra_parameters():
    assert set(AGENTS).issubset(CAPABILITIES)
    assert get_capability("audio.from_session").cost == "tts"
    assert set(get_capability("audio.from_session").required_params) == {"context_id", "session_id", "through_position"}
    with pytest.raises(ValidationError, match="Unknown capability"):
        get_capability("invented")
    capability = get_capability("audio.from_session")
    base = {"context_id": str(uuid4()), "session_id": str(uuid4()), "through_position": 2}
    for payload in ({}, {**base, "arbitrary": "private text"}, {**base, "through_position": -1}):
        with pytest.raises(ValidationError, match="Invalid capability parameters"):
            capability.validate(payload)
    assert capability.validate(base).through_position == 2
    assert get_capability("data_reset").confirmation == "destructive"
    assert get_capability("evidence").confirmation == "destructive"
    assert get_capability("learner_model").kind == "required"


def test_confirmation_gate_does_not_invoke_handler(session_factory, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("destructive handler ran")

    monkeypatch.setitem(AGENTS["data_reset"], "handler", forbidden)
    with session_factory() as db:
        with pytest.raises(ValidationError, match="confirmation"):
            asyncio.run(execute_capability(db, owner_id=uuid4(), name="data_reset", payload={}))


def test_typed_adapter_calls_existing_handler_with_owned_context(session_factory, monkeypatch):
    async def handler(db, *, owner_id, context_id, payload):
        assert context_id == payload_context
        assert payload["days"] == 14
        return {"upcoming": []}

    monkeypatch.setitem(AGENTS["planner"], "handler", handler)
    with session_factory() as db:
        owner, payload_context = learner_context(db)
        other, other_cid = learner_context(db)
        db.commit()
        assert asyncio.run(
            execute_capability(db, owner_id=owner, name="planner", payload={"context_id": str(payload_context)})
        ) == {"upcoming": []}
        with pytest.raises(ValidationError):
            asyncio.run(
                execute_capability(db, owner_id=other, name="planner", payload={"context_id": str(payload_context)})
            )


def test_audio_capability_freezes_cutoff_and_reuses_source(session_factory, monkeypatch, tmp_path):
    from app.services.audio_storage import LocalAudioStorage

    calls = []

    class FakeTTS:
        def generate(self, *, text):
            calls.append(text)
            return b"fake", "audio/mpeg", 1

    monkeypatch.setattr("app.services.audio.get_tts_provider", lambda: FakeTTS())
    monkeypatch.setattr("app.services.audio.get_audio_storage", lambda: LocalAudioStorage(tmp_path))
    with session_factory() as db:
        owner, cid = learner_context(db)
        second = StudySession(owner_id=owner, context_id=cid)
        db.add(second)
        db.flush()
        sid = second.id
        db.add_all(
            [
                ConversationMessage(
                    owner_id=owner, study_session_id=sid, role="user", content="Explain stacks", position=1
                ),
                ConversationMessage(
                    owner_id=owner,
                    study_session_id=sid,
                    role="assistant",
                    content="A stack is last in, first out.",
                    position=2,
                ),
            ]
        )
        db.commit()
        payload = {"context_id": str(cid), "session_id": str(sid), "through_position": 2}
        first = asyncio.run(execute_capability(db, owner_id=owner, name="audio.from_session", payload=payload))
        assert first["status"] == "READY" and "text" not in first
        db.add_all(
            [
                ConversationMessage(
                    owner_id=owner, study_session_id=sid, role="user", content="New question", position=3
                ),
                ConversationMessage(
                    owner_id=owner, study_session_id=sid, role="assistant", content="Later reply", position=4
                ),
            ]
        )
        db.commit()
        second_result = asyncio.run(execute_capability(db, owner_id=owner, name="audio.from_session", payload=payload))
        assert second_result["artifact_id"] == first["artifact_id"]
        assert len(calls) == 1
        from app.services.orchestration import run_workflow

        workflow, approval = asyncio.run(run_workflow(db, owner_id=owner, name="audio_from_session", payload=payload))
        assert workflow.status == "COMPLETED" and approval is None
        assert len(calls) == 1
        from uuid import UUID

        from app.db.models import AudioArtifact

        artifact = db.get(AudioArtifact, UUID(first["artifact_id"]))
        assert "Later reply" not in artifact.text
        other, other_cid = learner_context(db)
        db.commit()
        with pytest.raises(ValidationError):
            asyncio.run(execute_capability(db, owner_id=other, name="audio.from_session", payload=payload))
        with pytest.raises(ValidationError):
            asyncio.run(
                execute_capability(
                    db, owner_id=owner, name="audio.from_session", payload={**payload, "context_id": str(other_cid)}
                )
            )
