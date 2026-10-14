import importlib.util
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from app.db.models import Roadmap


def test_roadmap_provenance_migration_preserves_unknown_legacy_rows(engine):
    spec = importlib.util.spec_from_file_location(
        "roadmap_provenance_migration", Path("database/migrations/versions/0022_roadmap_provenance.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with engine.begin() as connection:
        connection.execute(Roadmap.__table__.insert().values(
            id=uuid4(), owner_id=uuid4(), **{'goal': 'Legacy goal'}))
        module.op = Operations(MigrationContext.configure(connection))
        module.downgrade()
        module.upgrade()
        module.upgrade()
        assert connection.execute(text("SELECT goal, generation_mode, fallback_reason FROM roadmaps")).one() == (
            "Legacy goal", None, None,
        )
        module.downgrade()
        columns = {column["name"] for column in inspect(connection).get_columns("roadmaps")}
        assert {"id", "goal"} <= columns
        assert not {"generation_mode", "fallback_reason"} & columns
        assert connection.execute(text("SELECT goal FROM roadmaps")).scalar() == "Legacy goal"
