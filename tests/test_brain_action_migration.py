import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from tests.test_brain_snapshot import learner_context

from app.core.config import get_settings
from app.db.models import ConversationMessage, StudySession


def test_brain_migration_roundtrip_preserves_conversation(engine, session_factory, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "aria_brain_checkpoint_path", str(tmp_path / "checkpoints.db"))
    with session_factory() as db:
        owner, cid = learner_context(db)
        session = StudySession(owner_id=owner, context_id=cid)
        db.add(session)
        db.flush()
        db.add(
            ConversationMessage(
                owner_id=owner, study_session_id=session.id, role="assistant", content="Preserved reply", position=1
            )
        )
        db.commit()
    spec = importlib.util.spec_from_file_location(
        "brain_migration", Path("database/migrations/versions/0027_brain_actions.py")
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.downgrade()
        assert "action" not in {c["name"] for c in inspect(connection).get_columns("conversation_messages")}
        migration.upgrade()
        migration.upgrade()
        assert "brain_actions" in inspect(connection).get_table_names()
        assert "action" in {c["name"] for c in inspect(connection).get_columns("conversation_messages")}
        assert connection.execute(text("select content from conversation_messages")).scalar() == "Preserved reply"
    if engine.dialect.name == "sqlite":
        import sqlite3

        with sqlite3.connect(tmp_path / "checkpoints.db") as connection:
            tables = {r[0] for r in connection.execute("select name from sqlite_master where type='table'")}
            assert {"checkpoints", "writes"} <= tables
