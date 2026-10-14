import os
import time
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models import AudioArtifact, AudioProgress, LearningContext, Note
from app.services.audio import (
    delete_audio,
    generate_audio,
    load_audio_bytes,
    process_audio_queue,
    requeue_missing_audio,
    sweep_audio_files,
)
from app.services.audio_storage import LocalAudioStorage


class FakeTTS:
    def generate(self, *, text):
        return b"AUDIO", "audio/mpeg", 10


@pytest.fixture()
def storage(monkeypatch, tmp_path):
    storage = LocalAudioStorage(tmp_path)
    monkeypatch.setattr("app.services.audio.get_audio_storage", lambda: storage)
    return storage


def _create(db):
    owner, context, note = uuid4(), uuid4(), uuid4()
    db.add(LearningContext(id=context, owner_id=owner, title="Subject"))
    db.flush()
    db.add(Note(id=note, owner_id=owner, context_id=context, title="Note", body="Source"))
    db.commit()
    artifact = generate_audio(db, owner_id=owner, source_type="NOTE", source_id=note, provider=FakeTTS())
    return owner, context, artifact


@pytest.mark.parametrize("action", ["audio", "context", "reset"])
def test_every_delete_path_removes_committed_audio_files(engine, session_factory, storage, action):
    from app.services.account import reset_learner_data
    from app.services.data_management import delete_context_cascade

    with session_factory() as db:
        owner, context, artifact = _create(db)
        key = artifact.storage_key
        if action == "audio":
            delete_audio(db, owner_id=owner, artifact_id=artifact.id)
        elif action == "context":
            assert delete_context_cascade(db, owner_id=owner, context_id=context)
        else:
            reset_learner_data(db, owner_id=owner)
        assert storage.load(key) is None
        assert db.scalar(select(AudioArtifact.id)) is None


def test_failed_cleanup_survives_as_file_and_sweeper_retries(engine, session_factory, storage, monkeypatch):
    with session_factory() as db:
        owner, _, artifact = _create(db)
        key = artifact.storage_key
        original_delete = storage.delete
        monkeypatch.setattr(storage, "delete", lambda key: (_ for _ in ()).throw(OSError("unavailable")))
        delete_audio(db, owner_id=owner, artifact_id=artifact.id)
        assert storage.load(key) == b"AUDIO"
        path = storage._path(key)
        os.utime(path, (time.time() - 7200, time.time() - 7200))
        assert sweep_audio_files(db)["failed"] == 1
        monkeypatch.setattr(storage, "delete", original_delete)
        assert sweep_audio_files(db)["deleted"] == 1
        assert storage.load(key) is None


def test_sweeper_protects_references_active_tokens_and_new_files(engine, session_factory, storage):
    with session_factory() as db:
        owner, _, artifact = _create(db)
        active = uuid4()
        artifact.generation_token = active
        artifact.status = "PROCESSING"
        db.commit()
        keys = [artifact.storage_key]
        keys.append(storage.save(owner_id=owner, artifact_id=active, content_type="audio/mpeg", data=b"ACTIVE"))
        orphan = storage.save(owner_id=owner, artifact_id=uuid4(), content_type="audio/mpeg", data=b"ORPHAN")
        keys.append(orphan)
        for key in keys:
            os.utime(storage._path(key), (time.time() - 7200, time.time() - 7200))
        recent = storage.save(owner_id=owner, artifact_id=uuid4(), content_type="audio/mpeg", data=b"RECENT")
        assert sweep_audio_files(db)["deleted"] == 1
        assert storage.load(orphan) is None
        assert storage.load(keys[0]) == b"AUDIO"
        assert storage.load(keys[1]) == b"ACTIVE"
        assert storage.load(recent) == b"RECENT"


def test_database_only_restore_requeues_missing_audio_and_preserves_progress(engine, session_factory, storage):
    with session_factory() as db:
        owner, _, artifact = _create(db)
        db.add(AudioProgress(owner_id=owner, artifact_id=artifact.id, position_seconds=4))
        db.commit()
        storage.delete(artifact.storage_key)
        assert requeue_missing_audio(db) == 1
        assert requeue_missing_audio(db) == 0
        assert process_audio_queue(db, provider=FakeTTS()) == 1
        db.refresh(artifact)
        assert artifact.status == "READY"
        assert load_audio_bytes(artifact) == b"AUDIO"
        assert db.scalar(select(AudioProgress.position_seconds)) == 4


@pytest.mark.parametrize("action", ["audio", "context", "reset"])
def test_failed_database_deletion_keeps_audio_bytes(engine, session_factory, storage, monkeypatch, action):
    from app.services.account import reset_learner_data
    from app.services.data_management import delete_context_cascade

    with session_factory() as db:
        owner, context, artifact = _create(db)
        key, artifact_id = artifact.storage_key, artifact.id
        monkeypatch.setattr(db, "commit", lambda: (_ for _ in ()).throw(RuntimeError("commit failed")))
        with pytest.raises(RuntimeError, match="commit failed"):
            if action == "audio":
                delete_audio(db, owner_id=owner, artifact_id=artifact_id)
            elif action == "context":
                delete_context_cascade(db, owner_id=owner, context_id=context)
            else:
                reset_learner_data(db, owner_id=owner)
        db.rollback()
        assert storage.load(key) == b"AUDIO"
        assert db.get(AudioArtifact, artifact_id) is not None


def test_audio_delete_with_saved_progress_removes_children_before_parent(engine, session_factory, storage):
    with session_factory() as db:
        owner, _, artifact = _create(db)
        artifact_id, key = artifact.id, artifact.storage_key
        db.add(AudioProgress(owner_id=owner, artifact_id=artifact_id, position_seconds=7, completed=False))
        db.commit()
        delete_audio(db, owner_id=owner, artifact_id=artifact_id)
    with session_factory() as verifier:
        assert verifier.get(AudioArtifact, artifact_id) is None
        assert verifier.scalar(select(AudioProgress.id).where(AudioProgress.artifact_id == artifact_id)) is None
    assert storage.load(key) is None
