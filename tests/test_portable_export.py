import base64
import json
from uuid import uuid4

from app.db.models import (
    AudioArtifact,
    ConversationMessage,
    LearningContext,
    Note,
    Resource,
    ResourceChunk,
    StudySession,
)
from app.services.data_management import export_learner_data, stream_learner_data


def test_export_has_no_old_collection_or_message_caps(engine, session_factory):
    owner, context, session = uuid4(), uuid4(), uuid4()
    with session_factory() as db:
        db.add(LearningContext(id=context, owner_id=owner, title="Subject"))
        db.add(StudySession(id=session, owner_id=owner, context_id=context))
        db.flush()
        db.add_all([Note(owner_id=owner, context_id=context, title=f"Note {n}", body="Body")
                    for n in range(5001)])
        db.add_all([ConversationMessage(owner_id=owner, study_session_id=session, position=n,
                                       role="assistant", content=f"Message {n}", fallback_used=True)
                    for n in range(501)])
        db.commit()
        exported = export_learner_data(db, owner_id=owner)
    assert exported["metadata"]["schema_version"] == 2
    assert exported["metadata"]["truncated"] is False
    assert len(exported["notes"]) == exported["record_counts"]["notes"] == 5001
    assert len(exported["conversation_messages"]) == 501
    assert {row["position"] for row in exported["conversation_messages"]} == set(range(501))
    assert all(row["fallback_used"] for row in exported["conversation_messages"])
    assert all(row["context_id"] == str(context) for row in exported["notes"])
    assert all(row["study_session_id"] == str(session) for row in exported["conversation_messages"])


def test_export_reconstructs_ids_relationships_and_original_bytes(engine, session_factory, monkeypatch, tmp_path):
    from app.services.audio_storage import LocalAudioStorage

    storage = LocalAudioStorage(tmp_path)
    monkeypatch.setattr("app.services.audio.get_audio_storage", lambda: storage)
    owner, context, resource, chunk, audio = [uuid4() for _ in range(5)]
    original = b"\x00PDF original\xff"
    sound = b"\x00recorded audio\xff"
    key = storage.save(owner_id=owner, artifact_id=audio, content_type="audio/wav", data=sound)
    with session_factory() as db:
        db.add(LearningContext(id=context, owner_id=owner, title="Subject"))
        db.flush()
        db.add(Resource(id=resource, owner_id=owner, context_id=context, title="PDF",
                        resource_type="PDF", source_text="Original text", raw_bytes=original))
        db.flush()
        db.add(ResourceChunk(id=chunk, owner_id=owner, resource_id=resource, content="Excerpt",
                             chunk_index=0, embedding_json=[0.1, 0.2]))
        db.add(AudioArtifact(id=audio, owner_id=owner, source_id=resource, source_type="RESOURCE",
                             text="Original text", status="READY", storage_key=key))
        db.add(Note(owner_id=uuid4(), context_id=context, title="Other learner", body="Private"))
        db.commit()
        exported = export_learner_data(db, owner_id=owner)
    # Reconstruct the portable relational graph by its original primary keys.
    contexts = {row["id"]: row for row in exported["contexts"]}
    resources = {row["id"]: row for row in exported["resources"]}
    chunks = {row["id"]: row for row in exported["resource_chunks"]}
    assert contexts[resources[str(resource)]["context_id"]]["title"] == "Subject"
    assert resources[chunks[str(chunk)]["resource_id"]]["id"] == str(resource)
    assert resources[exported["audio_artifacts"][0]["source_id"]]["id"] == str(resource)
    assert base64.b64decode(resources[str(resource)]["raw_bytes"]) == original
    assert base64.b64decode(exported["audio_artifacts"][0]["audio_bytes"]) == sound
    assert "embedding_json" not in chunks[str(chunk)]
    assert exported["notes"] == []
    assert "Other learner" not in json.dumps(exported)


def test_export_marks_missing_files_and_can_cancel_before_reading_collections(engine, session_factory):
    owner = uuid4()
    with session_factory() as db:
        db.add(AudioArtifact(owner_id=owner, source_id=uuid4(), source_type="NOTE",
                             text="Text", status="READY", storage_key=None))
        db.commit()
        stream = stream_learner_data(db, owner_id=owner)
        assert next(stream) == '{"metadata":'
        stream.close()
        exported = export_learner_data(db, owner_id=owner)
    assert exported["audio_artifacts"][0]["audio_bytes"] is None
    assert exported["audio_artifacts"][0]["audio_bytes_status"] == "unavailable"


def test_postgres_export_keeps_one_snapshot_during_concurrent_changes(engine, session_factory):
    import pytest
    from sqlalchemy import select

    if engine.dialect.name != "postgresql":
        pytest.skip("Independent PostgreSQL snapshot connections required")
    owner, context_id, note_id = uuid4(), uuid4(), uuid4()
    with session_factory() as db:
        db.add(LearningContext(id=context_id, owner_id=owner, title="Before export"))
        db.flush()
        db.add(Note(id=note_id, owner_id=owner, context_id=context_id, title="Original note", body="Preserved"))
        db.commit()
    with session_factory() as reader:
        stream = stream_learner_data(reader, owner_id=owner)
        prefix = next(stream)  # establishes the REPEATABLE READ snapshot
        with session_factory() as writer:
            context = writer.get(LearningContext, context_id)
            context.title = "After export started"
            writer.delete(writer.get(Note, note_id))
            writer.add(Note(owner_id=owner, context_id=context_id, title="New note", body="Later commit"))
            writer.commit()
        exported = json.loads(prefix + "".join(stream))
    assert exported["contexts"][0]["title"] == "Before export"
    assert [row["id"] for row in exported["notes"]] == [str(note_id)]
    assert exported["record_counts"]["notes"] == 1
    with session_factory() as verifier:
        assert verifier.get(LearningContext, context_id).title == "After export started"
        assert verifier.get(Note, note_id) is None
        assert verifier.scalar(select(Note).where(Note.owner_id == owner)).title == "New note"


def test_postgres_cancelled_export_releases_snapshot_connection(engine, session_factory):
    import pytest

    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL connection-pool inspection required")
    baseline = engine.pool.checkedout()
    with session_factory() as db:
        stream = stream_learner_data(db, owner_id=uuid4())
        next(stream)
        assert engine.pool.checkedout() == baseline + 1
        stream.close()
        assert engine.pool.checkedout() == baseline
