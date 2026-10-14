import importlib.util
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from app.db.models import AudioArtifact


def test_audio_lease_migration_preserves_audio_and_is_repeatable(engine, session_factory):
    with session_factory() as db:
        artifact = AudioArtifact(owner_id=uuid4(), source_id=uuid4(), source_type="NOTE",
                                 text="Legacy", status="READY", audio_bytes=b"LEGACY")
        db.add(artifact)
        db.commit()
    spec = importlib.util.spec_from_file_location(
        "audio_lease_migration", Path("database/migrations/versions/0021_audio_leases.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with engine.begin() as connection:
        module.op = Operations(MigrationContext.configure(connection))
        module.downgrade()
        assert "lease_until" not in {column["name"] for column in inspect(connection).get_columns("audio_artifacts")}
        module.upgrade()
        module.upgrade()
        row = connection.execute(text(
            "SELECT status, audio_bytes, generation_attempts, generation_token, lease_until FROM audio_artifacts"
        )).one()
        assert row == ("READY", b"LEGACY", 0, None, None)
