"""Phase 12.7 generalized idempotency: workflow replay via Idempotency-Key."""

from fastapi.testclient import TestClient

MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time. "
    "A precedence graph detects cycles that indicate non-serializable schedules."
)


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse", "display_name": "Learner"},
    )
    assert response.status_code == 201
    return response.json()


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _learner(client: TestClient, email: str) -> tuple[str, str]:
    session = register(client, email)
    context = client.post(
        "/api/v1/contexts", headers=headers(session["access_token"]), json={"title": "DBMS"}
    ).json()
    client.post(
        "/api/v1/resources/text",
        headers=headers(session["access_token"]),
        json={"context_id": context["id"], "title": "Locks", "text": MATERIAL},
    )
    return session["access_token"], context["id"]


def test_workflow_with_idempotency_key_replays_stored_response(client: TestClient) -> None:
    token, context_id = _learner(client, "idem@example.com")
    headers_with_key = {
        **headers(token),
        "Idempotency-Key": "wf-gen-notes-1",
    }

    first = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers=headers_with_key,
        json={"payload": {"context_id": context_id}},
    )
    assert first.status_code == 201
    first_body = first.json()
    assert first_body["status"] == "COMPLETED"

    second = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers=headers_with_key,
        json={"payload": {"context_id": context_id}},
    )
    assert second.status_code == 201
    assert second.json() == first_body

    workflows = client.get("/api/v1/orchestration/workflows", headers=headers(token)).json()
    assert len(workflows) == 1


def test_workflow_without_idempotency_key_runs_twice(client: TestClient) -> None:
    token, context_id = _learner(client, "twice@example.com")
    for _ in range(2):
        response = client.post(
            "/api/v1/orchestration/workflows/generate_notes",
            headers=headers(token),
            json={"payload": {"context_id": context_id}},
        )
        assert response.status_code == 201

    workflows = client.get("/api/v1/orchestration/workflows", headers=headers(token)).json()
    assert len(workflows) == 2


def test_idempotency_key_is_scoped_per_learner(client: TestClient) -> None:
    first = register(client, "idem-a@example.com")
    second = register(client, "idem-b@example.com")
    key = {"Idempotency-Key": "shared-key"}

    first_started = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers={**headers(first["access_token"]), **key},
        json={"payload": {}},
    )
    # No context for this learner -> the payload is accepted but the workflow
    # fails; what matters here is that the key is recorded for learner A only.
    assert first_started.status_code == 201

    second_started = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers={**headers(second["access_token"]), **key},
        json={"payload": {}},
    )
    assert second_started.status_code == 201
    assert second_started.json()["workflow_id"] != first_started.json()["workflow_id"]


def test_idempotency_record_recovers_from_concurrent_insert(
    engine, session_factory, monkeypatch
) -> None:
    from uuid import uuid4

    from sqlalchemy import select

    from app.db.models import IdempotencyKey
    from app.services import idempotency

    owner_id = uuid4()
    db = session_factory()
    try:
        # Pre-insert the winning row so the first insert attempt collides.
        db.add(
            IdempotencyKey(
                owner_id=owner_id,
                scope="wf",
                key="race-1",
                response_status=200,
                response_json={"v": 1},
            )
        )
        db.commit()

        real_find = idempotency.find
        calls = {"n": 0}

        def stale_find(db, *, owner_id, scope, key):
            calls["n"] += 1
            if calls["n"] == 1:
                return None  # simulate a concurrent writer winning between find and insert
            return real_find(db, owner_id=owner_id, scope=scope, key=key)

        monkeypatch.setattr(idempotency, "find", stale_find)

        entry = idempotency.record(
            db, owner_id=owner_id, scope="wf", key="race-1", status=201, response={"v": 2}
        )
        assert calls["n"] >= 2
        assert entry.response_json == {"v": 2}

        stored = db.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.owner_id == owner_id, IdempotencyKey.key == "race-1"
            )
        )
        assert stored is not None
        assert stored.response_json == {"v": 2}
    finally:
        db.close()


def test_reserve_reports_in_progress_for_duplicate(engine, session_factory) -> None:
    from uuid import uuid4

    from app.services import idempotency

    owner_id = uuid4()
    db = session_factory()
    try:
        assert (
            idempotency.reserve(db, owner_id=owner_id, scope="wf", key="reserve-1")
            == "ok"
        )
        # A second request with the same key sees the in-flight reservation.
        second = session_factory()
        try:
            assert (
                idempotency.reserve(second, owner_id=owner_id, scope="wf", key="reserve-1")
                == "in_progress"
            )
        finally:
            second.close()
    finally:
        db.close()


def test_reserve_takes_over_expired_completed_row(engine, session_factory) -> None:
    from uuid import uuid4

    from sqlalchemy import select

    from app.db.models import IdempotencyKey
    from app.services import idempotency

    owner_id = uuid4()
    db = session_factory()
    try:
        db.add(
            IdempotencyKey(
                owner_id=owner_id,
                scope="wf",
                key="reserve-2",
                response_status=200,
                response_json={"v": 1},
            )
        )
        db.commit()
        assert (
            idempotency.reserve(db, owner_id=owner_id, scope="wf", key="reserve-2")
            == "ok"
        )
        row = db.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.owner_id == owner_id, IdempotencyKey.key == "reserve-2"
            )
        )
        assert row is not None
        assert row.response_json is None  # reservation cleared for a fresh run
    finally:
        db.close()


def test_in_flight_duplicate_returns_409(client: TestClient, session_factory) -> None:
    from uuid import UUID

    from app.db.models import IdempotencyKey

    session = register(client, "idem-flight@example.com")
    learner_id = UUID(session["learner_id"])
    client.post(
        "/api/v1/contexts",
        headers=headers(session["access_token"]),
        json={"title": "DBMS"},
    )

    # Simulate a concurrent request that already reserved the key.
    db = session_factory()
    try:
        db.add(
            IdempotencyKey(
                owner_id=learner_id,
                scope="workflow:generate_notes",
                key="in-flight-key",
                response_status=None,
                response_json=None,
            )
        )
        db.commit()
    finally:
        db.close()

    duplicate = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers={
            **headers(session["access_token"]),
            "Idempotency-Key": "in-flight-key",
        },
        json={"payload": {}},
    )
    assert duplicate.status_code == 409
    assert "already in progress" in duplicate.json()["detail"]


def test_purge_expired_removes_only_dead_rows(engine, session_factory) -> None:
    """Standalone sweeper: expired completed + stale in-progress rows are
    removed; live reservations (future TTL) are never touched."""
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from sqlalchemy import select

    from app.db.models import IdempotencyKey
    from app.services import idempotency

    owner_id = uuid4()
    db = session_factory()
    try:
        now = datetime.now(UTC)
        # Expired completed row (no longer replayable) -> removed.
        db.add(
            IdempotencyKey(
                owner_id=owner_id, scope="wf", key="done-old",
                response_status=200, response_json={"v": 1},
                expires_at=now - timedelta(hours=2),
            )
        )
        # Stale in-progress row (crashed execution) -> removed.
        db.add(
            IdempotencyKey(
                owner_id=owner_id, scope="wf", key="stale-reservation",
                response_status=None, response_json=None,
                expires_at=now - timedelta(hours=2),
            )
        )
        # Live completed row (still replayable) -> kept.
        db.add(
            IdempotencyKey(
                owner_id=owner_id, scope="wf", key="done-live",
                response_status=200, response_json={"v": 2},
                expires_at=now + timedelta(hours=1),
            )
        )
        # Live in-progress reservation (another request executing) -> kept.
        db.add(
            IdempotencyKey(
                owner_id=owner_id, scope="wf", key="live-reservation",
                response_status=None, response_json=None,
                expires_at=now + timedelta(hours=1),
            )
        )
        db.commit()

        removed = idempotency.purge_expired(db)
        assert removed == 2

        remaining = {
            row.key
            for row in db.scalars(
                select(IdempotencyKey).where(IdempotencyKey.owner_id == owner_id)
            ).all()
        }
        assert remaining == {"done-live", "live-reservation"}

        # Idempotent: a second sweep removes nothing.
        assert idempotency.purge_expired(db) == 0
    finally:
        db.close()


def test_idempotency_sweep_job_purges_expired(engine, monkeypatch) -> None:
    """The scheduled job uses the shared engine/SessionLocal and runs under
    the advisory lock; verify it removes expired rows end to end."""
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker

    from app.db.models import IdempotencyKey
    from app.jobs import scheduler as scheduler_mod

    owner_id = uuid4()
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = factory()
    try:
        db.add(
            IdempotencyKey(
                owner_id=owner_id, scope="wf", key="sweep-me",
                response_status=200, response_json={"v": 1},
                expires_at=datetime.now(UTC) - timedelta(hours=3),
            )
        )
        db.add(
            IdempotencyKey(
                owner_id=owner_id, scope="wf", key="keep-me",
                response_status=200, response_json={"v": 1},
                expires_at=datetime.now(UTC) + timedelta(hours=3),
            )
        )
        db.commit()

        # Point the job's engine/SessionLocal at the test database.
        monkeypatch.setattr(
            "app.db.session.engine", engine, raising=True
        )
        monkeypatch.setattr(
            "app.db.session.SessionLocal", factory, raising=True
        )
        scheduler_mod.run_idempotency_sweep_job()

        remaining = {
            row.key
            for row in db.scalars(
                select(IdempotencyKey).where(IdempotencyKey.owner_id == owner_id)
            ).all()
        }
        assert remaining == {"keep-me"}
    finally:
        db.close()
