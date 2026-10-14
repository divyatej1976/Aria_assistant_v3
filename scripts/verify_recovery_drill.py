"""Verify encrypted PostgreSQL backup plus separate audio-file recovery.

Run only against disposable databases named aria_review_drill_source and
aria_review_drill_restore. Supply their URLs via ARIA_DRILL_SOURCE_URL and
ARIA_DRILL_RESTORE_URL. No existing schema or user volume is removed.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from cryptography.fernet import Fernet
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import AudioArtifact, LearningContext, Note
from app.services.audio_storage import LocalAudioStorage
from app.services.backup import create_backup


def main() -> int:
    source_url = os.environ["ARIA_DRILL_SOURCE_URL"]
    restore_url = os.environ["ARIA_DRILL_RESTORE_URL"]
    if (make_url(source_url).database != "aria_review_drill_source"
            or make_url(restore_url).database != "aria_review_drill_restore"):
        raise ValueError("Recovery drill requires the explicitly named disposable databases")
    source, destination = create_engine(source_url), create_engine(restore_url)
    try:
        if inspect(source).get_table_names() or inspect(destination).get_table_names():
            raise ValueError("Recovery drill databases must be empty")
        with source.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(source)
        with tempfile.TemporaryDirectory(prefix="aria-recovery-drill-") as temporary:
            root = Path(temporary)
            original_audio = LocalAudioStorage(root / "original-audio")
            owner, context_id, note_id, artifact_id = (uuid4() for _ in range(4))
            audio = b"RIFF-disposable-review-audio-bytes"
            storage_key = original_audio.save(owner_id=owner, artifact_id=artifact_id,
                                             content_type="audio/wav", data=audio)
            with Session(source) as db:
                db.add(LearningContext(id=context_id, owner_id=owner, title="Recovery subject"))
                db.flush()
                db.add(Note(id=note_id, owner_id=owner, context_id=context_id,
                            title="Recovery note", body="Preserved relationship and Unicode: biology \u2192 mastery"))
                db.flush()
                db.add(AudioArtifact(id=artifact_id, owner_id=owner, source_type="NOTE", source_id=note_id,
                                     text="Recovery narration", status="READY", storage_key=storage_key,
                                     content_type="audio/wav", duration_seconds=1))
                db.commit()
            key = Fernet.generate_key().decode()
            archive = create_backup(database_url=source_url, out_dir=root / "backups", encryption_key=key)
            assert archive.suffix == ".enc"
            assert not list((root / "backups").glob("*.dump.gz"))
            # Audio is a separate volume: preserve and restore it independently
            # of pg_dump, then verify the restored database's storage reference.
            shutil.copytree(root / "original-audio", root / "saved-audio")
            shutil.rmtree(root / "original-audio")
            environment = {**os.environ, "DATABASE_URL": restore_url, "ARIA_BACKUP_ENCRYPTION_KEY": key}
            restored = subprocess.run([sys.executable, "scripts/restore_db.py", str(archive)],
                                      env=environment, capture_output=True, timeout=60)
            assert restored.returncode == 0, "Database archive restore failed"
            shutil.copytree(root / "saved-audio", root / "restored-audio")
            with Session(destination) as db:
                context = db.get(LearningContext, context_id)
                note = db.get(Note, note_id)
                artifact = db.get(AudioArtifact, artifact_id)
                assert context.title == "Recovery subject"
                assert note.context_id == context.id and note.owner_id == owner
                assert "\u2192" in note.body
                assert artifact.source_id == note.id and artifact.status == "READY"
                assert LocalAudioStorage(root / "restored-audio").load(artifact.storage_key) == audio
                assert len(list(db.scalars(select(Note)))) == 1
            wrong_key = {**environment, "ARIA_BACKUP_ENCRYPTION_KEY": Fernet.generate_key().decode()}
            rejected = subprocess.run([sys.executable, "scripts/restore_db.py", str(archive)],
                                      env=wrong_key, capture_output=True, timeout=60)
            assert rejected.returncode == 1, "Wrong-key encrypted archive was not rejected"
            assert key.encode() not in rejected.stderr
        print("Recovery drill passed: encrypted pg_dump/pg_restore, relationships, "
              "Unicode, audio bytes, wrong key")
        return 0
    finally:
        source.dispose()
        destination.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
