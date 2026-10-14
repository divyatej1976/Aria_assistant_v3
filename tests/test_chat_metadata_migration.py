import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text


def test_chat_metadata_upgrade_preserves_legacy_history_and_is_repeatable(engine):
    spec = importlib.util.spec_from_file_location(
        "chat_metadata_migration", Path("database/migrations/versions/0020_chat_fallback.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with engine.begin() as connection:
        # Replace only this unreferenced table with its legacy shape in the
        # shared fixture database, so the regression also runs on PostgreSQL.
        connection.execute(text("DROP TABLE conversation_messages"))
        connection.execute(text("CREATE TABLE conversation_messages (id INTEGER PRIMARY KEY, content TEXT NOT NULL)"))
        connection.execute(text("INSERT INTO conversation_messages VALUES (1, 'Legacy answer')"))
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        module.upgrade()
        row = connection.execute(text("SELECT content, fallback_used FROM conversation_messages")).one()
        assert row == ("Legacy answer", None)
        connection.execute(text("UPDATE conversation_messages SET fallback_used = TRUE"))
        assert connection.execute(text("SELECT fallback_used FROM conversation_messages")).scalar() == 1
        module.downgrade()
        assert "fallback_used" not in {column["name"] for column in inspect(connection).get_columns("conversation_messages")}
        assert connection.execute(text("SELECT content FROM conversation_messages")).scalar() == "Legacy answer"
