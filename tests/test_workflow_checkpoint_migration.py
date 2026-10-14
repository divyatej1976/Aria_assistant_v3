import importlib.util
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from app.db.models import IdempotencyKey


def test_workflow_checkpoint_migration_preserves_existing_responses(engine):
    spec = importlib.util.spec_from_file_location(
        "workflow_checkpoint_migration", Path("database/migrations/versions/0025_workflow_checkpoint.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with engine.begin() as connection:
        connection.execute(IdempotencyKey.__table__.insert().values(
            id=uuid4(), owner_id=uuid4(), scope="workflow:generate_notes", key="preserved",
            request_fingerprint="fingerprint", response_status=201, response_json={"status": "COMPLETED"},
        ))
        module.op = Operations(MigrationContext.configure(connection))
        module.downgrade()
        module.upgrade()
        module.upgrade()
        row = connection.execute(text(
            "SELECT key, request_fingerprint, response_status, response_json, workflow_id FROM idempotency_keys"
        )).one()
        assert row.key == "preserved"
        assert row.request_fingerprint == "fingerprint"
        assert row.response_status == 201
        assert "COMPLETED" in str(row.response_json)
        assert row.workflow_id is None
        module.downgrade()
        assert "workflow_id" not in {col["name"] for col in inspect(connection).get_columns("idempotency_keys")}
        assert connection.execute(text("SELECT key FROM idempotency_keys")).scalar() == "preserved"
