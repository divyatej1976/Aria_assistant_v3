import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.models import Assessment, LearningContext


def test_daily_review_migration_preserves_assessments_and_enforces_one_per_day(engine):
    spec = importlib.util.spec_from_file_location("daily_review_migration", Path("database/migrations/versions/0026_daily_review.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    owner, context = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(LearningContext.__table__.insert().values(id=context, owner_id=owner, title="Subject"))
        connection.execute(Assessment.__table__.insert().values(id=uuid4(), owner_id=owner, context_id=context))
        module.op = Operations(MigrationContext.configure(connection))
        module.downgrade()
        assert "daily_review_date" not in {column["name"] for column in inspect(connection).get_columns("assessments")}
        module.upgrade()
        assert connection.execute(text("SELECT COUNT(*) FROM assessments")).scalar() == 1
        for day in ["2026-10-14", "2026-10-15", None, None]:
            connection.execute(Assessment.__table__.insert().values(id=uuid4(), owner_id=owner, context_id=context, daily_review_date=day))
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(Assessment.__table__.insert().values(id=uuid4(), owner_id=owner, context_id=context, daily_review_date="2026-10-14"))
