import importlib.util
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select, text

from app.db.models import IdempotencyKey


def test_payload_migration_keeps_legacy_response_unknown_and_is_repeatable(engine):
    spec = importlib.util.spec_from_file_location(
        "payload_migration", Path("database/migrations/versions/0023_idempotency_payload.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with engine.begin() as connection:
        connection.execute(IdempotencyKey.__table__.insert().values(
            id=uuid4(), owner_id=uuid4(), **{'scope': 'legacy', 'key': 'legacy', 'response_json': {'legacy': True}}))
        module.op = Operations(MigrationContext.configure(connection))
        module.downgrade()
        module.upgrade()
        module.upgrade()
        assert connection.execute(text("SELECT request_fingerprint FROM idempotency_keys")).scalar() is None
        assert connection.execute(select(IdempotencyKey.response_json)).scalar() == {"legacy": True}
        module.downgrade()
        assert "request_fingerprint" not in {c["name"] for c in inspect(connection).get_columns("idempotency_keys")}
        assert connection.execute(select(IdempotencyKey.response_json)).scalar() == {"legacy": True}
