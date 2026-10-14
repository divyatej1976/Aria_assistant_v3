from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.dependencies import get_db
from app.db.models import LearningContext, Note, RevisionItem
from app.schemas.notes import (
    GenerateRequest,
    NoteCreateRequest,
    NoteResponse,
    NoteUpdateRequest,
    ReviewRequest,
)
from app.security.dependencies import CurrentLearner
from app.security.rate_limit import rate_limited
from app.services.notes import (
    build_note_pdf,
    create_note,
    delete_note,
    due_notes,
    generate_note,
    get_owned_note,
    list_notes,
    review_note,
    revision_item,
    revision_items_for,
    update_note,
)
from app.services.progress import record_activity

router = APIRouter(prefix="/api/v1/notes", tags=["notes"])
Db = Annotated[Session, Depends(get_db)]


def _ai_rate_limit():
    settings = get_settings()
    return rate_limited(
        settings.aria_rate_limit_requests, settings.aria_rate_limit_window_seconds
    )


def get_owned_context(db: Session, *, context_id: UUID, owner_id: UUID) -> LearningContext:
    context = db.scalar(
        select(LearningContext).where(
            LearningContext.id == context_id, LearningContext.owner_id == owner_id
        )
    )
    if context is None:
        raise HTTPException(status_code=404, detail="Learning context not found")
    return context


def note_response(
    db: Session, *, owner_id: UUID, note: Note, item: RevisionItem | None = None
) -> NoteResponse:
    if item is None:
        item = revision_item(db, owner_id=owner_id, note_id=note.id)
    return NoteResponse(
        id=str(note.id),
        context_id=str(note.context_id),
        title=note.title,
        body=note.body,
        concept_id=str(note.concept_id) if note.concept_id else None,
        study_session_id=str(note.study_session_id) if note.study_session_id else None,
        created_at=note.created_at,
        state=item.state if item else None,
        interval_days=item.interval_days if item else None,
        next_review_at=item.next_review_at if item else None,
        last_outcome=item.last_outcome if item else None,
    )


@router.post("", response_model=NoteResponse, status_code=201)
def create(
    request: NoteCreateRequest, learner: CurrentLearner, db: Db
) -> NoteResponse:
    get_owned_context(db, context_id=request.context_id, owner_id=learner.id)
    note = create_note(
        db,
        owner_id=learner.id,
        context_id=request.context_id,
        title=request.title,
        body=request.body,
        concept_id=request.concept_id,
    )
    return note_response(db, owner_id=learner.id, note=note)


@router.get("", response_model=list[NoteResponse])
def list_notes_route(context_id: UUID, learner: CurrentLearner, db: Db) -> list[NoteResponse]:
    get_owned_context(db, context_id=context_id, owner_id=learner.id)
    notes = list_notes(db, owner_id=learner.id, context_id=context_id)
    items = revision_items_for(
        db, owner_id=learner.id, note_ids=[note.id for note in notes]
    )
    return [
        note_response(db, owner_id=learner.id, note=note, item=items.get(note.id))
        for note in notes
    ]


@router.get("/due", response_model=list[NoteResponse])
def due(context_id: UUID, learner: CurrentLearner, db: Db) -> list[NoteResponse]:
    get_owned_context(db, context_id=context_id, owner_id=learner.id)
    notes = due_notes(db, owner_id=learner.id, context_id=context_id)
    items = revision_items_for(
        db, owner_id=learner.id, note_ids=[note.id for note in notes]
    )
    return [
        note_response(db, owner_id=learner.id, note=note, item=items.get(note.id))
        for note in notes
    ]


@router.post("/generate", response_model=NoteResponse, status_code=201, dependencies=[Depends(_ai_rate_limit())])
async def generate(
    request: GenerateRequest, learner: CurrentLearner, db: Db
) -> NoteResponse:
    get_owned_context(db, context_id=request.context_id, owner_id=learner.id)
    try:
        note = await generate_note(
            db,
            owner_id=learner.id,
            context_id=request.context_id,
            study_session_id=request.study_session_id,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return note_response(db, owner_id=learner.id, note=note)


@router.get("/{note_id}", response_model=NoteResponse)
def detail(note_id: UUID, learner: CurrentLearner, db: Db) -> NoteResponse:
    try:
        note = get_owned_note(db, owner_id=learner.id, note_id=note_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return note_response(db, owner_id=learner.id, note=note)


@router.put("/{note_id}", response_model=NoteResponse)
def update(
    note_id: UUID, request: NoteUpdateRequest, learner: CurrentLearner, db: Db
) -> NoteResponse:
    note = update_note(
        db, owner_id=learner.id, note_id=note_id, title=request.title, body=request.body
    )
    return note_response(db, owner_id=learner.id, note=note)


@router.delete("/{note_id}")
def delete(note_id: UUID, learner: CurrentLearner, db: Db) -> dict[str, object]:
    try:
        delete_note(db, owner_id=learner.id, note_id=note_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": True}


@router.post("/{note_id}/review", response_model=NoteResponse)
def review(
    note_id: UUID, request: ReviewRequest, learner: CurrentLearner, db: Db
) -> NoteResponse:
    try:
        note = review_note(
            db, owner_id=learner.id, note_id=note_id, outcome=request.outcome
        )
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_activity(db, owner_id=learner.id, activity_type="revision", source_id=note.id)
    return note_response(db, owner_id=learner.id, note=note)


@router.get("/{note_id}/download")
def download(note_id: UUID, learner: CurrentLearner, db: Db) -> Response:
    try:
        note = get_owned_note(db, owner_id=learner.id, note_id=note_id)
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    content = build_note_pdf(note)
    safe_title = (
        "".join(
            char for char in note.title if char.isascii() and (char.isalnum() or char in " -_")
        ).strip()
        or "note"
    )
    filename = f"{safe_title[:80]}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
