"""Actual process exit after committed work must not authorize a replay."""

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import IdempotencyKey, Note, Workflow
from app.services.idempotency import purge_expired, reserve


def test_worker_exit_preserves_committed_work_and_blocks_reexecution(engine, tmp_path):
    file_backed = engine.dialect.name == "sqlite"
    database_url = (f"sqlite:///{(tmp_path / 'crashed-worker.db').as_posix()}" if file_backed
                    else engine.url.render_as_string(hide_password=False))
    script = """
import asyncio
import os
import sys
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.db.models import LearningContext, Note
from app.services import orchestration
from app.services.idempotency import reserve

engine = create_engine(sys.argv[1])
Base.metadata.create_all(engine)
with Session(engine, expire_on_commit=False) as db:
    owner = uuid4()
    context = LearningContext(owner_id=owner, title="Crash test")
    db.add(context)
    db.commit()
    claim = uuid4()
    assert reserve(db, owner_id=owner, scope="workflow:generate_notes", key="crash",
                   claim_id=claim, request_fingerprint="same-request") == "ok"
    async def interrupted(db, *, owner_id, workflow, payload):
        db.add(Note(owner_id=owner_id, context_id=context.id, title="Committed once", body="Preserved work"))
        db.commit()
        os._exit(23)
    orchestration._advance = interrupted
    asyncio.run(orchestration.run_workflow(db, owner_id=owner, name="generate_notes",
        payload={"context_id": str(context.id)},
        idempotency_claim=("workflow:generate_notes", "crash", claim)))
"""
    environment = {**os.environ, "PYTHONPATH": str(Path("backend").resolve()), "GROQ_API_KEY": ""}
    result = subprocess.run([sys.executable, "-c", script, database_url], env=environment,
                            capture_output=True, timeout=60)
    assert result.returncode == 23, result.stderr.decode("utf-8", errors="replace")
    if file_backed:
        engine = create_engine(database_url)
    try:
        with Session(engine) as db:
            checkpoint = db.scalar(select(IdempotencyKey))
            workflow = db.scalar(select(Workflow))
            assert checkpoint.workflow_id == workflow.id
            assert checkpoint.response_status is None
            assert checkpoint.response_json is None
            assert workflow.status == "RUNNING"
            assert len(list(db.scalars(select(Note)))) == 1
            checkpoint.expires_at = datetime.now(UTC) - timedelta(days=2)
            db.commit()
            assert purge_expired(db) == 0
            assert reserve(db, owner_id=checkpoint.owner_id, scope=checkpoint.scope, key=checkpoint.key,
                           claim_id=uuid4(), request_fingerprint="same-request") == "recovery_required"
            assert len(list(db.scalars(select(Note)))) == 1
            assert len(list(db.scalars(select(Workflow)))) == 1
    finally:
        if file_backed:
            engine.dispose()
