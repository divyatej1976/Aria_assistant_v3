from uuid import uuid4

from sqlalchemy import select

from app.db.models import Feedback


def _token(client) -> str:
    response = client.post("/api/v1/auth/register", json={
        "email": f"fb-{uuid4().hex[:8]}@example.com", "password": "correct-horse-9", "display_name": "L"})
    assert response.status_code == 201
    return response.json()["access_token"]


def test_learners_can_report_problems_and_rate_answers(client, session_factory) -> None:
    auth = {"Authorization": f"Bearer {_token(client)}"}
    report = client.post("/api/v1/feedback", headers=auth, json={
        "kind": "report", "message": "Audio never finished", "page": "/app/audio", "user_agent": "test"})
    assert report.status_code == 201 and report.json()["status"] == "new"
    answer = uuid4()
    rated = client.post("/api/v1/feedback", headers=auth, json={
        "kind": "answer", "rating": "down", "reason": "outdated", "answer_id": str(answer)})
    assert rated.status_code == 201
    with session_factory() as db:
        rows = db.scalars(select(Feedback).order_by(Feedback.created_at)).all()
        assert [(r.kind, r.rating, r.reason, r.page) for r in rows] == [
            ("report", None, None, "/app/audio"), ("answer", "down", "outdated", None)]
        assert rows[1].answer_id == answer


def test_feedback_must_be_complete_and_signed_in(client) -> None:
    auth = {"Authorization": f"Bearer {_token(client)}"}
    assert client.post("/api/v1/feedback", headers=auth, json={"kind": "report", "message": "  "}).status_code == 422
    assert client.post("/api/v1/feedback", headers=auth, json={"kind": "answer", "rating": "up"}).status_code == 422
    # Signed out: refused (the CSRF guard answers before the sign-in check does).
    assert client.post("/api/v1/feedback", json={"kind": "report", "message": "hi"}).status_code in (401, 403)


def test_health_is_reachable_under_api(client) -> None:
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_learners_can_rate_aria_with_stars(client) -> None:
    auth = {"Authorization": f"Bearer {_token(client)}"}
    assert client.post("/api/v1/feedback", headers=auth, json={
        "kind": "experience", "rating": "4", "message": "Cards are great"}).status_code == 201
    assert client.post("/api/v1/feedback", headers=auth, json={"kind": "experience", "rating": "up"}).status_code == 422
