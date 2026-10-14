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


def test_workflow_key_rejects_changed_payload_and_preserves_original_replay(client):
    token, context = _learner(client, "payload-conflict@example.com")
    auth = {**headers(token), "Idempotency-Key": "bound-payload"}
    url = "/api/v1/orchestration/workflows/generate_notes"
    original_payload = {"payload": {"context_id": context}}
    original = client.post(url, headers=auth, json=original_payload)
    assert original.status_code == 201
    changed = client.post(url, headers=auth, json={"payload": {"context_id": context, "extra": "different"}})
    assert changed.status_code == 409
    replay = client.post(url, headers=auth, json=original_payload)
    assert replay.json() == original.json()
    assert len(client.get("/api/v1/orchestration/workflows", headers=headers(token)).json()) == 1


def test_request_fingerprint_is_order_independent():
    from app.services.idempotency import fingerprint

    assert fingerprint({"a": 1, "nested": {"x": 2, "y": 3}}) == fingerprint({"nested": {"y": 3, "x": 2}, "a": 1})
    assert fingerprint({"a": 1}) != fingerprint({"a": "1"})


def test_completion_between_replay_check_and_reservation_does_not_execute_again(client, monkeypatch):
    from app.api.routes import orchestration as route_module

    token, context = _learner(client, "completed-race@example.com")
    auth = {**headers(token), "Idempotency-Key": "completion-race"}
    url = "/api/v1/orchestration/workflows/generate_notes"
    payload = {"payload": {"context_id": context}}
    original = client.post(url, headers=auth, json=payload)
    assert original.status_code == 201
    find = route_module.find_idempotency
    calls = 0

    def stale_initial_check(*args, **kwargs):
        nonlocal calls
        calls += 1
        return None if calls == 1 else find(*args, **kwargs)

    async def unexpected_execution(*args, **kwargs):
        raise AssertionError("Completed work must not be executed again")

    monkeypatch.setattr(route_module, "find_idempotency", stale_initial_check)
    monkeypatch.setattr(route_module, "run_workflow", unexpected_execution)
    replay = client.post(url, headers=auth, json=payload)
    assert replay.status_code == 201
    assert replay.json() == original.json()


def test_idempotency_key_is_scoped_per_learner(client: TestClient) -> None:
    first_token, first_context = _learner(client, "idem-a@example.com")
    second_token, second_context = _learner(client, "idem-b@example.com")
    key = {"Idempotency-Key": "shared-key"}

    first_started = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers={**headers(first_token), **key},
        json={"payload": {"context_id": first_context}},
    )
    # Both valid payloads use the same key, but each learner gets a separate workflow.
    assert first_started.status_code == 201

    second_started = client.post(
        "/api/v1/orchestration/workflows/generate_notes",
        headers={**headers(second_token), **key},
        json={"payload": {"context_id": second_context}},
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
    from datetime import UTC, datetime, timedelta
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
                expires_at=datetime.now(UTC) - timedelta(seconds=1),
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


def test_reservation_cannot_erase_live_completed_response(session_factory):
    from uuid import uuid4

    from app.services import idempotency

    owner = uuid4()
    with session_factory() as db:
        idempotency.record(db, owner_id=owner, scope="wf", key="completed", status=201, response={"result": 1})
        assert idempotency.reserve(db, owner_id=owner, scope="wf", key="completed") == "completed"
        assert idempotency.find(db, owner_id=owner, scope="wf", key="completed").response_json == {"result": 1}


def test_stale_observation_cannot_reclaim_already_renewed_reservation(session_factory, monkeypatch):
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from app.db.models import IdempotencyKey
    from app.services import idempotency

    owner = uuid4()
    with session_factory() as db:
        row = IdempotencyKey(owner_id=owner, scope="wf", key="takeover",
                             expires_at=datetime.now(UTC) - timedelta(seconds=1))
        db.add(row)
        db.commit()
        original_find = idempotency.find
        calls = 0

        def stale_find(db, **kwargs):
            nonlocal calls
            result = original_find(db, **kwargs)
            calls += 1
            if calls == 1:
                # Another claimant renewed the exact expiry the caller observed.
                from sqlalchemy import update

                db.execute(update(IdempotencyKey).where(IdempotencyKey.id == result.id).values(
                    expires_at=datetime.now(UTC) + timedelta(minutes=5)),
                    execution_options={"synchronize_session": False})
                db.commit()
            return result

        monkeypatch.setattr(idempotency, "find", stale_find)
        assert idempotency.reserve(db, owner_id=owner, scope="wf", key="takeover") == "in_progress"


def test_release_cannot_delete_response_completed_after_lookup(session_factory, monkeypatch):
    from types import SimpleNamespace
    from uuid import uuid4

    from sqlalchemy import update

    from app.db.models import IdempotencyKey
    from app.services import idempotency

    owner = uuid4()
    with session_factory() as db:
        assert idempotency.reserve(db, owner_id=owner, scope="wf", key="release-race") == "ok"
        original_find = idempotency.find

        def stale_find(db, **kwargs):
            entry = original_find(db, **kwargs)
            observed = SimpleNamespace(id=entry.id, expires_at=entry.expires_at, response_json=None)
            db.execute(update(IdempotencyKey).where(IdempotencyKey.id == entry.id).values(
                response_status=201, response_json={"completed": True}),
                execution_options={"synchronize_session": False})
            db.commit()
            return observed

        monkeypatch.setattr(idempotency, "find", stale_find)
        idempotency.release(db, owner_id=owner, scope="wf", key="release-race")
        entry = original_find(db, owner_id=owner, scope="wf", key="release-race")
        assert entry.response_json == {"completed": True}
        assert entry.response_status == 201


def test_release_cannot_delete_reservation_renewed_after_lookup(session_factory, monkeypatch):
    from datetime import timedelta
    from types import SimpleNamespace
    from uuid import uuid4

    from sqlalchemy import update

    from app.db.models import IdempotencyKey
    from app.services import idempotency

    owner = uuid4()
    with session_factory() as db:
        assert idempotency.reserve(db, owner_id=owner, scope="wf", key="release-renewal") == "ok"
        original_find = idempotency.find
        renewed = None

        def stale_find(db, **kwargs):
            nonlocal renewed
            entry = original_find(db, **kwargs)
            observed = SimpleNamespace(id=entry.id, expires_at=entry.expires_at, response_json=None)
            renewed = entry.expires_at + timedelta(minutes=5)
            db.execute(update(IdempotencyKey).where(IdempotencyKey.id == entry.id).values(expires_at=renewed),
                       execution_options={"synchronize_session": False})
            db.commit()
            return observed

        monkeypatch.setattr(idempotency, "find", stale_find)
        idempotency.release(db, owner_id=owner, scope="wf", key="release-renewal")
        entry = original_find(db, owner_id=owner, scope="wf", key="release-renewal")
        assert entry is not None
        assert entry.expires_at == renewed
        assert entry.response_status is None


def test_postgres_concurrent_expired_claim_has_one_winner(engine, session_factory, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from datetime import UTC, datetime, timedelta
    from threading import Barrier
    from uuid import uuid4

    import pytest

    from app.db.models import IdempotencyKey
    from app.services import idempotency

    if engine.dialect.name != "postgresql":
        pytest.skip("Requires independent PostgreSQL connections")
    owner = uuid4()
    with session_factory() as db:
        db.add(IdempotencyKey(owner_id=owner, scope="wf", key="concurrent-expired",
                             expires_at=datetime.now(UTC) - timedelta(seconds=10)))
        db.commit()
    barrier = Barrier(2)
    original_find = idempotency.find

    def synchronized_find(db, **kwargs):
        entry = original_find(db, **kwargs)
        if not db.info.get("observed_expiry"):
            db.info["observed_expiry"] = True
            barrier.wait(timeout=10)
        return entry

    monkeypatch.setattr(idempotency, "find", synchronized_find)

    def claim():
        with session_factory() as db:
            return idempotency.reserve(db, owner_id=owner, scope="wf", key="concurrent-expired")

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: claim(), range(2)))
    assert sorted(results) == ["in_progress", "ok"]
    with session_factory() as db:
        row = original_find(db, owner_id=owner, scope="wf", key="concurrent-expired")
        assert row.response_status is None
        assert row.expires_at > datetime.now(UTC)


def test_old_claim_cannot_release_or_record_new_claim(session_factory):
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    import pytest
    from sqlalchemy import update

    from app.db.models import IdempotencyKey
    from app.services import idempotency

    owner, old_claim, new_claim = uuid4(), uuid4(), uuid4()
    with session_factory() as db:
        assert idempotency.reserve(db, owner_id=owner, scope="wf", key="fenced", claim_id=old_claim) == "ok"
        db.execute(update(IdempotencyKey).where(IdempotencyKey.id == old_claim).values(
            expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        db.commit()
        assert idempotency.reserve(db, owner_id=owner, scope="wf", key="fenced", claim_id=new_claim) == "ok"
        idempotency.release(db, owner_id=owner, scope="wf", key="fenced", claim_id=old_claim)
        assert idempotency.find(db, owner_id=owner, scope="wf", key="fenced").id == new_claim
        with pytest.raises(idempotency.ClaimLost):
            idempotency.record(db, owner_id=owner, scope="wf", key="fenced", claim_id=old_claim,
                               status=201, response={"old": True})
        idempotency.record(db, owner_id=owner, scope="wf", key="fenced", claim_id=new_claim,
                           status=201, response={"new": True})
        idempotency.release(db, owner_id=owner, scope="wf", key="fenced", claim_id=old_claim)
        assert idempotency.find(db, owner_id=owner, scope="wf", key="fenced").response_json == {"new": True}


def test_renew_only_extends_the_current_live_unfinished_claim(session_factory):
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from sqlalchemy import update

    from app.db.models import IdempotencyKey
    from app.services import idempotency

    owner, claim = uuid4(), uuid4()
    with session_factory() as db:
        assert idempotency.reserve(db, owner_id=owner, scope="wf", key="renew", claim_id=claim) == "ok"
        near_expiry = datetime.now(UTC) + timedelta(seconds=10)
        db.execute(update(IdempotencyKey).where(IdempotencyKey.id == claim).values(expires_at=near_expiry))
        db.commit()
        assert not idempotency.renew(db, owner_id=uuid4(), scope="wf", key="renew", claim_id=claim)
        assert not idempotency.renew(db, owner_id=owner, scope="other", key="renew", claim_id=claim)
        assert not idempotency.renew(db, owner_id=owner, scope="wf", key="other", claim_id=claim)
        assert not idempotency.renew(db, owner_id=owner, scope="wf", key="renew", claim_id=uuid4())
        assert idempotency.renew(db, owner_id=owner, scope="wf", key="renew", claim_id=claim)
        row = idempotency.find(db, owner_id=owner, scope="wf", key="renew")
        assert row.expires_at.replace(tzinfo=UTC) > near_expiry
        expired = datetime.now(UTC) - timedelta(seconds=1)
        db.execute(update(IdempotencyKey).where(IdempotencyKey.id == claim).values(expires_at=expired))
        db.commit()
        assert not idempotency.renew(db, owner_id=owner, scope="wf", key="renew", claim_id=claim)
        replacement = uuid4()
        assert idempotency.reserve(db, owner_id=owner, scope="wf", key="renew", claim_id=replacement) == "ok"
        assert not idempotency.renew(db, owner_id=owner, scope="wf", key="renew", claim_id=claim)
        idempotency.record(db, owner_id=owner, scope="wf", key="renew", claim_id=replacement,
                           status=201, response={"done": True})
        assert not idempotency.renew(db, owner_id=owner, scope="wf", key="renew", claim_id=replacement)
        assert idempotency.find(db, owner_id=owner, scope="wf", key="renew").response_json == {"done": True}


def test_in_flight_duplicate_returns_409(client: TestClient, session_factory) -> None:
    from uuid import UUID

    from app.db.models import IdempotencyKey
    from app.services.idempotency import fingerprint

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
                    request_fingerprint=fingerprint({"payload": {}}),
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


def test_claim_heartbeat_renews_and_stops_on_exit(session_factory, monkeypatch):
    from threading import Event
    from types import SimpleNamespace
    from uuid import uuid4

    from app.services import idempotency

    called = Event()
    calls = []
    def renewal(db, **kwargs):
        calls.append(kwargs)
        called.set()
        return True
    monkeypatch.setattr(idempotency, "get_settings", lambda: SimpleNamespace(aria_idempotency_ttl_seconds=0.15))
    monkeypatch.setattr(idempotency, "renew", renewal)
    owner, claim = uuid4(), uuid4()
    with session_factory() as db:
        with idempotency.keep_claim_alive(db, owner_id=owner, scope="wf", key="heartbeat", claim_id=claim):
            assert called.wait(2)
        count = len(calls)
        called.clear()
        assert not called.wait(0.15)
        assert len(calls) == count
        assert calls[0] == {"owner_id": owner, "scope": "wf", "key": "heartbeat", "claim_id": claim}


def test_claim_heartbeat_loss_fences_successful_exit(session_factory, monkeypatch):
    from threading import Event
    from types import SimpleNamespace
    from uuid import uuid4

    import pytest

    from app.services import idempotency

    called = Event()
    def renewal(db, **kwargs):
        called.set()
        return False
    monkeypatch.setattr(idempotency, "get_settings", lambda: SimpleNamespace(aria_idempotency_ttl_seconds=0.15))
    monkeypatch.setattr(idempotency, "renew", renewal)
    with session_factory() as db:
        with pytest.raises(idempotency.ClaimLost):
            with idempotency.keep_claim_alive(db, owner_id=uuid4(), scope="wf", key="lost", claim_id=uuid4()):
                assert called.wait(2)


def test_claim_heartbeat_stops_without_masking_handler_error(session_factory, monkeypatch):
    from threading import Event
    from types import SimpleNamespace
    from uuid import uuid4

    import pytest

    from app.services import idempotency

    called = Event()
    def renewal(db, **kwargs):
        called.set()
        return True
    monkeypatch.setattr(idempotency, "get_settings", lambda: SimpleNamespace(aria_idempotency_ttl_seconds=0.15))
    monkeypatch.setattr(idempotency, "renew", renewal)
    with session_factory() as db:
        with pytest.raises(ValueError, match="handler failure"):
            with idempotency.keep_claim_alive(db, owner_id=uuid4(), scope="wf", key="failed", claim_id=uuid4()):
                assert called.wait(2)
                raise ValueError("handler failure")
        called.clear()
        assert not called.wait(0.15)


def test_postgres_heartbeat_prevents_takeover_after_original_expiry(engine, session_factory, monkeypatch):
    from threading import Event
    from time import sleep
    from types import SimpleNamespace
    from uuid import uuid4

    import pytest

    from app.services import idempotency

    if engine.dialect.name != "postgresql":
        pytest.skip("Independent PostgreSQL connections required")
    monkeypatch.setattr(idempotency, "get_settings", lambda: SimpleNamespace(aria_idempotency_ttl_seconds=0.6))
    renewed = Event()
    original_renew = idempotency.renew
    def observed_renew(db, **kwargs):
        result = original_renew(db, **kwargs)
        if result:
            renewed.set()
        return result
    monkeypatch.setattr(idempotency, "renew", observed_renew)
    owner, claim = uuid4(), uuid4()
    with session_factory() as db:
        assert idempotency.reserve(db, owner_id=owner, scope="wf", key="slow", claim_id=claim) == "ok"
        with idempotency.keep_claim_alive(db, owner_id=owner, scope="wf", key="slow", claim_id=claim):
            assert renewed.wait(3)
            sleep(0.7)
            with session_factory() as competitor:
                assert idempotency.reserve(competitor, owner_id=owner, scope="wf", key="slow", claim_id=uuid4()) == "in_progress"
        idempotency.record(db, owner_id=owner, scope="wf", key="slow", claim_id=claim,
                           status=201, response={"done": True})
        assert idempotency.find(db, owner_id=owner, scope="wf", key="slow").response_json == {"done": True}


def test_postgres_slow_workflow_http_duplicate_stays_blocked(client, engine, monkeypatch):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from time import sleep
    from types import SimpleNamespace
    from uuid import uuid4

    import pytest

    from app.api.routes import orchestration
    from app.services import idempotency

    if engine.dialect.name != "postgresql":
        pytest.skip("Independent PostgreSQL connections required")
    session = register(client, "slow-http@example.com")
    monkeypatch.setattr(idempotency, "get_settings", lambda: SimpleNamespace(aria_idempotency_ttl_seconds=0.6))
    entered, finish = Event(), Event()
    calls = []
    workflow_id = uuid4()
    async def held_workflow(db, **kwargs):
        calls.append(kwargs)
        entered.set()
        assert await asyncio.to_thread(finish.wait, 5)
        return SimpleNamespace(id=workflow_id, status="COMPLETED"), None
    monkeypatch.setattr(orchestration, "run_workflow", held_workflow)
    request_headers = {**headers(session["access_token"]), "Idempotency-Key": "slow-http"}
    url = "/api/v1/orchestration/workflows/generate_notes"
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(client.post, url, headers=request_headers, json={"payload": {}})
        try:
            assert entered.wait(5)
            sleep(0.9)
            duplicate = client.post(url, headers=request_headers, json={"payload": {}})
            assert duplicate.status_code == 409
            assert len(calls) == 1
        finally:
            finish.set()
        response = first.result(timeout=5)
    assert response.status_code == 201
    assert response.json()["workflow_id"] == str(workflow_id)
    replay = client.post(url, headers=request_headers, json={"payload": {}})
    assert replay.status_code == 201
    assert replay.json() == response.json()
    assert len(calls) == 1


def test_idempotency_timing_configuration_requires_positive_seconds():
    import pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    for field in ("aria_idempotency_ttl_seconds", "aria_idempotency_sweep_interval_seconds"):
        for value in (0, -1):
            with pytest.raises(ValidationError) as error:
                Settings(_env_file=None, aria_env="development", **{field: value})
            assert any(item["loc"] == (field,) for item in error.value.errors())
        settings = Settings(_env_file=None, aria_env="development", **{field: 1})
        assert getattr(settings, field) == 1


def test_claim_heartbeat_error_fences_response_without_private_diagnostics(session_factory, monkeypatch, caplog):
    from threading import Event
    from types import SimpleNamespace
    from uuid import uuid4

    import pytest

    from app.services import idempotency

    called = Event()
    def renewal(db, **kwargs):
        called.set()
        raise RuntimeError("private database diagnostic sentinel")
    monkeypatch.setattr(idempotency, "get_settings", lambda: SimpleNamespace(aria_idempotency_ttl_seconds=0.15))
    monkeypatch.setattr(idempotency, "renew", renewal)
    with session_factory() as db:
        with pytest.raises(idempotency.ClaimLost, match="renewal failed"):
            with idempotency.keep_claim_alive(db, owner_id=uuid4(), scope="wf", key="error", claim_id=uuid4()):
                assert called.wait(2)
    assert "RuntimeError" in caplog.text
    assert "private database diagnostic sentinel" not in caplog.text


def test_expired_workflow_checkpoint_blocks_repeated_committed_work(client, session_factory):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.db.models import IdempotencyKey, Workflow
    from app.services.idempotency import purge_expired

    token, context_id = _learner(client, "crash-checkpoint@example.com")
    request_headers = {**headers(token), "Idempotency-Key": "committed-before-response"}
    payload = {"payload": {"context_id": context_id}}
    first = client.post("/api/v1/orchestration/workflows/generate_notes", headers=request_headers, json=payload)
    assert first.status_code == 201
    workflow_id = first.json()["workflow_id"]
    before_notes = client.get("/api/v1/notes", headers=headers(token), params={"context_id": context_id}).json()
    assert before_notes
    # Model a worker that committed its domain work, then died before recording
    # the HTTP response: the separately durable checkpoint is all that remains.
    with session_factory() as db:
        checkpoint = db.scalar(select(IdempotencyKey).where(IdempotencyKey.key == request_headers["Idempotency-Key"]))
        assert str(checkpoint.workflow_id) == workflow_id
        interrupted_workflow = db.get(Workflow, checkpoint.workflow_id)
        interrupted_workflow.status = "RUNNING"
        checkpoint.response_status = None
        checkpoint.response_json = None
        checkpoint.expires_at = datetime.now(UTC) - timedelta(days=2)
        db.commit()
        assert purge_expired(db) == 0
    retry = client.post("/api/v1/orchestration/workflows/generate_notes", headers=request_headers, json=payload)
    assert retry.status_code == 409
    assert workflow_id in retry.json()["detail"]
    assert "may have committed changes" in retry.json()["detail"]
    assert client.get("/api/v1/notes", headers=headers(token), params={"context_id": context_id}).json() == before_notes
    history = client.get("/api/v1/orchestration/workflows", headers=headers(token)).json()
    assert len(history) == 1
    assert history[0]["status"] == "RECOVERY_REQUIRED"
    assert "interrupted" in history[0]["error_detail"]
    # Inserting an unrelated key must not purge the unresolved checkpoint either.
    other = client.post("/api/v1/orchestration/workflows/generate_notes", headers={
        **headers(token), "Idempotency-Key": "unrelated"}, json=payload)
    assert other.status_code == 201
    retry = client.post("/api/v1/orchestration/workflows/generate_notes", headers=request_headers, json=payload)
    assert retry.status_code == 409
