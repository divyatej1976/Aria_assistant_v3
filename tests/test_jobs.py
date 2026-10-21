"""Background jobs: claimed once, run in parallel, resumed after a hand-over, retried, guarded."""

from uuid import uuid4

from sqlalchemy import select
from tests.test_resources_study import create_context, headers, register

from app.db.models import Job, UploadChunk
from app.services import jobs


def test_a_job_is_claimed_by_only_one_worker(session_factory) -> None:
    with session_factory() as db:
        jobs.enqueue(db, kind="test", owner_id=uuid4(), target_id=uuid4(), start=False)
        first, second = jobs.claim(db), jobs.claim(db)
        assert first is not None and first.status == "running" and first.attempts == 1
        assert second is None  # the lease keeps every other worker off it


def test_enqueue_reuses_an_unfinished_job_for_the_same_target(session_factory) -> None:
    owner, target = uuid4(), uuid4()
    with session_factory() as db:
        a = jobs.enqueue(db, kind="test", owner_id=owner, target_id=target, start=False)
        b = jobs.enqueue(db, kind="test", owner_id=owner, target_id=target, start=False)
        assert a.id == b.id


def test_several_workers_each_take_a_different_job_at_once(session_factory) -> None:
    with session_factory() as db:
        targets = {jobs.enqueue(db, kind="test", owner_id=uuid4(), target_id=uuid4(), start=False).target_id
                   for _ in range(3)}
    # Three workers, each with its own connection, claim while the others still hold theirs.
    sessions = [session_factory() for _ in range(4)]
    claimed = [jobs.claim(db) for db in sessions]
    taken = {job.target_id for job in claimed[:3]}
    assert taken == targets  # every job taken, none twice: they now run side by side
    assert claimed[3] is None  # a fourth worker finds nothing left
    for db in sessions:
        db.close()


def test_a_job_that_runs_out_of_time_resumes_from_its_saved_progress(session_factory, monkeypatch) -> None:
    seen = []

    def stepwise(db, job, progress):
        step = progress.data.get("step", 0)
        seen.append(step)
        if step < 2:
            progress.save(step=step + 1)
            raise jobs.Continue()
    monkeypatch.setitem(jobs.HANDLERS, "test", stepwise)
    monkeypatch.setattr(jobs, "kick", lambda *args, **kwargs: None)
    with session_factory() as db:
        job = jobs.enqueue(db, kind="test", owner_id=uuid4(), target_id=uuid4(), start=False)
        while jobs.run_one(db):
            pass
        job = db.get(Job, job.id, populate_existing=True)
    assert seen == [0, 1, 2]
    assert job.status == "done" and job.attempts == 1  # hand-overs do not count as failures


def test_a_crashing_job_is_retried_then_marked_failed(session_factory, monkeypatch) -> None:
    def boom(db, job, progress):
        raise RuntimeError("provider down")
    monkeypatch.setitem(jobs.HANDLERS, "test", boom)
    with session_factory() as db:
        job = jobs.enqueue(db, kind="test", owner_id=uuid4(), target_id=uuid4(), start=False)
        while jobs.run_one(db):
            pass
        job = db.get(Job, job.id, populate_existing=True)
    assert job.status == "failed" and job.attempts == jobs.MAX_ATTEMPTS and "provider down" in job.error


def test_internal_endpoints_need_the_secret(client, monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "aria_cron_secret", "s3cret-for-tests")
    assert client.post("/api/v1/internal/work").status_code == 404
    assert client.post("/api/v1/internal/tick", headers={"Authorization": "Bearer wrong"}).status_code == 404
    ok = client.post("/api/v1/internal/tick", headers={"Authorization": "Bearer s3cret-for-tests"})
    assert ok.status_code == 200 and "jobs_started" in ok.json()


def test_a_large_file_uploads_in_pieces(client, session_factory) -> None:
    token = register(client, "pieces@example.com")["access_token"]
    context = create_context(client, token)
    text = ("Normalization removes redundancy. " * 400).encode()
    upload = uuid4()
    for seq, start in enumerate(range(0, len(text), 5000)):
        put = client.put(f"/api/v1/resources/uploads/{upload}/{seq}", headers=headers(token),
                         content=text[start:start + 5000])
        assert put.status_code == 204, put.text
    stranger = register(client, "pieces-stranger@example.com")["access_token"]
    stolen = client.post(f"/api/v1/resources/pdf?context_id={context}&upload_id={upload}", headers=headers(stranger))
    assert stolen.status_code in (400, 404)  # another learner cannot claim these pieces

    # The pieces are joined back in order and processed like a single upload.
    done = client.post(f"/api/v1/resources/pdf?context_id={context}&upload_id={upload}", headers=headers(token))
    assert done.status_code != 413 and "Empty PDF upload" not in done.text, done.text
    with session_factory() as db:
        assert db.scalars(select(UploadChunk)).all() == []  # pieces are removed once used
