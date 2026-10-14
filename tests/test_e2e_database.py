import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text


def resetter():
    script = Path(__file__).resolve().parents[1] / "frontend-v2/tests/create_test_db.py"
    spec = importlib.util.spec_from_file_location("e2e_database", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.reset_test_database


def test_e2e_reset_replaces_a_stale_schema(tmp_path):
    path = tmp_path / "e2e-old-schema.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with engine.begin() as db:
        db.execute(text("CREATE TABLE assessments (id TEXT PRIMARY KEY)"))
        db.execute(text("CREATE TABLE idempotency_keys (id TEXT PRIMARY KEY)"))
        db.execute(text("CREATE TABLE stale_marker (id TEXT PRIMARY KEY)"))
    engine.dispose()
    resetter()(str(path), workspace=tmp_path)
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    schema = inspect(engine)
    assert "daily_review_date" in {item["name"] for item in schema.get_columns("assessments")}
    assert "workflow_id" in {item["name"] for item in schema.get_columns("idempotency_keys")}
    assert "stale_marker" not in schema.get_table_names()
    engine.dispose()


@pytest.mark.parametrize("outside", [False, True])
def test_e2e_reset_refuses_app_data_or_an_escaping_path(tmp_path, outside):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = tmp_path / "e2e-outside.db" if outside else workspace / "aria_host.db"
    path.write_bytes(b"Must survive")
    with pytest.raises(ValueError):
        resetter()(str(path), workspace=workspace)
    assert path.read_bytes() == b"Must survive"
