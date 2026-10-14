import importlib.util
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from app.db.models import LearningContext


def test_concept_cache_migration_preserves_subject_and_is_repeatable(engine):
    spec = importlib.util.spec_from_file_location(
        "concept_cache_migration", Path("database/migrations/versions/0024_concept_sync_cache.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with engine.begin() as connection:
        connection.execute(LearningContext.__table__.insert().values(
            id=uuid4(), owner_id=uuid4(), title="Preserved subject", configuration={"custom": "preserved"},
            concept_sync_fingerprint="old", concept_sync_names=["apple"],
        ))
        module.op = Operations(MigrationContext.configure(connection))
        module.downgrade()
        module.upgrade()
        module.upgrade()
        row = connection.execute(text(
            "SELECT title, concept_sync_fingerprint, concept_sync_names FROM learning_contexts"
        )).one()
        assert tuple(row) == ("Preserved subject", None, None)
        assert "preserved" in str(connection.execute(text("SELECT configuration FROM learning_contexts")).scalar())
        module.downgrade()
        columns = {column["name"] for column in inspect(connection).get_columns("learning_contexts")}
        assert "concept_sync_fingerprint" not in columns
        assert "concept_sync_names" not in columns
        assert connection.execute(text("SELECT title FROM learning_contexts")).scalar() == "Preserved subject"
