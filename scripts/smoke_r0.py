"""End-to-end smoke of the R0 loop against a running backend.

Requires the backend to be up (e.g. `uvicorn app.main:app --app-dir backend`
with DATABASE_URL pointing at a real database). Verifies the full learner
journey over the public API and reports PASS/FAIL per step.
"""

import os
import sys
import uuid

import fitz
import httpx

BASE = os.environ.get("BASE_URL", "http://localhost:8000")
MATERIAL = (
    "Two-phase locking uses a growth phase and a shrink phase. "
    "Strict two-phase locking releases every lock only at commit time. "
    "A precedence graph detects cycles that indicate non-serializable schedules. "
    "Conflict serializability is a subset of view serializability for most schedules. "
    "Deadlock detection requires waiting for a cycle in the resource wait-for graph."
)

client = httpx.Client(base_url=BASE, timeout=30.0)
failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}  {detail}")
        failures.append(name)


def make_pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def register(email: str) -> dict:
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse"})
    check("register", response.status_code == 201, response.text)
    return response.json()


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    token = register(f"smoke-{uuid.uuid4().hex[:10]}@example.com")["access_token"]
    h = headers(token)

    me = client.get("/api/v1/auth/me", headers=h)
    check("auth/me", me.status_code == 200, me.text)

    context = client.post(
        "/api/v1/contexts",
        headers=h,
        json={"title": "DBMS", "description": "Smoke context", "configuration": {"mastery_level": "beginner"}},
    )
    check("create context", context.status_code == 201, context.text)
    context_id = context.json()["id"]

    text_resource = client.post(
        "/api/v1/resources/text",
        headers=h,
        json={"context_id": context_id, "title": "Locks", "text": MATERIAL},
    )
    check(
        "add text resource -> READY",
        text_resource.status_code == 201 and text_resource.json()["processing_status"] == "READY",
        text_resource.text,
    )

    pdf_resource = client.post(
        f"/api/v1/resources/pdf?context_id={context_id}&title=Notes.pdf",
        headers={**h, "Content-Type": "application/pdf"},
        content=make_pdf_bytes("Conflict serializability is tested with precedence graphs."),
    )
    check(
        "add PDF resource -> READY",
        pdf_resource.status_code == 201 and pdf_resource.json()["processing_status"] == "READY",
        pdf_resource.text,
    )

    session = client.post("/api/v1/study/sessions", headers=h, json={"context_id": context_id})
    check("create study session", session.status_code == 201, session.text)
    session_id = session.json()["id"]

    answer = client.post(
        f"/api/v1/study/sessions/{session_id}/messages",
        headers=h,
        json={"content": "When does strict two-phase locking release its locks?"},
    )
    check("grounded question answered", answer.status_code == 200 and answer.json()["content"], answer.text)

    follow_up = client.post(
        f"/api/v1/study/sessions/{session_id}/messages",
        headers=h,
        json={"content": "Explain quantum chromodynamics and the banana diet"},
    )
    fallback = follow_up.json()["content"]
    check(
        "insufficient-material fallback",
        follow_up.status_code == 200 and "could not find enough relevant information" in fallback,
        follow_up.text,
    )

    assessment = client.post(
        "/api/v1/assessments",
        headers=h,
        json={"context_id": context_id, "format": "mcq", "question_count": 3, "difficulty": "medium"},
    )
    check("create assessment", assessment.status_code == 201, assessment.text)
    assessment_id = assessment.json()["id"]

    attempt = client.post(f"/api/v1/assessments/{assessment_id}/attempts", headers=h)
    check("start attempt", attempt.status_code == 201, attempt.text)
    attempt_id = attempt.json()["attempt_id"]
    questions = attempt.json()["questions"]

    autosave = client.put(
        f"/api/v1/assessments/{assessment_id}/attempts/{attempt_id}/answers",
        headers=h,
        json={"answers": {questions[0]["id"]: "A"}},
    )
    check("autosave answers", autosave.status_code == 200, autosave.text)

    key = f"smoke-{uuid.uuid4().hex}"
    submitted = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        headers=h,
        json={"idempotency_key": key, "answers": {q["id"]: "A" for q in questions}},
    )
    check("submit attempt", submitted.status_code == 200 and submitted.json()["status"] == "COMPLETED", submitted.text)
    first_result = submitted.json()

    resubmitted = client.post(
        f"/api/v1/assessments/{assessment_id}/attempts/{attempt_id}/submit",
        headers=h,
        json={"idempotency_key": key, "answers": {q["id"]: "A" for q in questions}},
    )
    check(
        "idempotent resubmit (same result)",
        resubmitted.status_code == 200
        and resubmitted.json()["evaluation_id"] == first_result["evaluation_id"]
        and resubmitted.json()["score"] == first_result["score"],
        resubmitted.text,
    )

    adaptation = client.get(f"/api/v1/contexts/{context_id}/adaptation", headers=h)
    check("adaptation summary", adaptation.status_code == 200, adaptation.text)
    body = adaptation.json()
    check("concept states present", len(body["states"]) > 0, adaptation.text)
    check(
        "weak states + decisions",
        any(s["state"] in ("NEEDS_REVIEW", "DEVELOPING") for s in body["states"])
        and any(d["decision_type"] in ("FOCUS_STUDY", "RETEST_TARGETED") for d in body["decisions"]),
        adaptation.text,
    )

    evidence = client.get(f"/api/v1/contexts/{context_id}/evidence", headers=h)
    check("evidence list", evidence.status_code == 200 and len(evidence.json()) > 0, evidence.text)
    target = next(item for item in evidence.json() if item["signal"] == "INCORRECT")
    invalidated = client.post(
        f"/api/v1/contexts/{context_id}/evidence/{target['id']}/invalidate", headers=h
    )
    check("invalidate evidence recomputes", invalidated.status_code == 200, invalidated.text)

    note = client.post(
        "/api/v1/notes",
        headers=h,
        json={"context_id": context_id, "title": "Locks note", "body": "Two-phase locking summary."},
    )
    check("create note", note.status_code == 201 and note.json()["state"] == "NEW", note.text)
    note_id = note.json()["id"]

    generated = client.post(
        "/api/v1/notes/generate", headers=h, json={"context_id": context_id}
    )
    check(
        "generate note (fallback)",
        generated.status_code == 201 and generated.json()["title"],
        generated.text,
    )

    reviewed = client.post(
        f"/api/v1/notes/{note_id}/review",
        headers=h,
        json={"outcome": "good"},
    )
    check(
        "review advances schedule",
        reviewed.status_code == 200 and reviewed.json()["interval_days"] == 3,
        reviewed.text,
    )

    due = client.get(f"/api/v1/notes/due?context_id={context_id}", headers=h)
    check("notes due queue empty for fresh note", due.status_code == 200 and due.json() == [], due.text)

    downloaded = client.get(f"/api/v1/notes/{note_id}/download", headers=h)
    check(
        "note PDF download",
        downloaded.status_code == 200
        and downloaded.headers["content-type"].startswith("application/pdf")
        and downloaded.content[:5] == b"%PDF-",
        downloaded.text[:80],
    )

    second_token = register(f"smoke-{uuid.uuid4().hex[:10]}@example.com")["access_token"]
    isolated = client.get(
        f"/api/v1/contexts/{context_id}/adaptation", headers=headers(second_token)
    )
    check("learner isolation", isolated.status_code == 404, isolated.text)

    print()
    if failures:
        print(f"SMOKE FAILED: {len(failures)} failing step(s): {', '.join(failures)}")
        return 1
    print("SMOKE PASSED: full R0 journey verified end-to-end")
    return 0


if __name__ == "__main__":
    sys.exit(main())
