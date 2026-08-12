"""Learner notes: CRUD, generation, spaced revision, and PDF export."""

import io
from datetime import UTC, datetime, timedelta
from uuid import UUID
from xml.sax.saxutils import escape

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.providers import LiteLLMGroqProvider
from app.assessment.schema import NoteDraftSchema
from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.models import (
    ConversationMessage,
    LearningContext,
    Note,
    RevisionItem,
)
from app.services.concepts import context_chunks

REVIEW_INTERVALS = [1, 3, 7, 14, 30]


def _now() -> datetime:
    return datetime.now(UTC)


def get_owned_note(db: Session, *, owner_id: UUID, note_id: UUID) -> Note:
    note = db.scalar(
        select(Note).where(Note.id == note_id, Note.owner_id == owner_id)
    )
    if note is None:
        raise ValidationError("Note not found")
    return note


def list_notes(db: Session, *, owner_id: UUID, context_id: UUID) -> list[Note]:
    return list(
        db.scalars(
            select(Note)
            .where(Note.owner_id == owner_id, Note.context_id == context_id)
            .order_by(Note.created_at.desc())
        )
    )


def revision_item(db: Session, *, owner_id: UUID, note_id: UUID) -> RevisionItem | None:
    return db.scalar(
        select(RevisionItem).where(
            RevisionItem.owner_id == owner_id, RevisionItem.note_id == note_id
        )
    )


def create_note(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    title: str,
    body: str,
    concept_id: UUID | None = None,
    study_session_id: UUID | None = None,
    source_refs: list[dict] | None = None,
) -> Note:
    note = Note(
        owner_id=owner_id,
        context_id=context_id,
        title=title,
        body=body,
        concept_id=concept_id,
        study_session_id=study_session_id,
        source_refs=source_refs or [],
    )
    db.add(note)
    db.flush()
    db.add(
        RevisionItem(
            owner_id=owner_id,
            note_id=note.id,
            state="NEW",
            interval_days=1,
            next_review_at=_now() + timedelta(days=1),
        )
    )
    db.commit()
    db.refresh(note)
    return note


def update_note(
    db: Session, *, owner_id: UUID, note_id: UUID, title: str, body: str
) -> Note:
    note = get_owned_note(db, owner_id=owner_id, note_id=note_id)
    note.title = title
    note.body = body
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, *, owner_id: UUID, note_id: UUID) -> None:
    note = get_owned_note(db, owner_id=owner_id, note_id=note_id)
    db.execute(
        delete(RevisionItem).where(
            RevisionItem.note_id == note.id, RevisionItem.owner_id == owner_id
        )
    )
    db.flush()
    db.delete(note)
    db.commit()


def _note_material(
    db: Session, *, owner_id: UUID, context_id: UUID, study_session_id: UUID | None
) -> str:
    if study_session_id is not None:
        messages = db.scalars(
            select(ConversationMessage)
            .where(
                ConversationMessage.study_session_id == study_session_id,
                ConversationMessage.owner_id == owner_id,
            )
            .order_by(ConversationMessage.position)
        ).all()
        lines = [
            f"{'Learner' if message.role == 'user' else 'ARIA'}: {message.content[:500]}"
            for message in messages
        ]
        return "\n".join(lines) if lines else ""
    chunks = context_chunks(db, owner_id=owner_id, context_id=context_id)
    return "\n\n".join(
        f"[{index + 1}] {chunk.content[:400]}" for index, chunk in enumerate(chunks[:12])
    )


def _deterministic_draft(material: str, context_title: str) -> NoteDraftSchema:
    lines = [line for line in material.split("\n") if line.strip()]
    return NoteDraftSchema(
        title=f"{context_title} — Study notes",
        body="\n\n".join(f"- {line.strip()}" for line in lines[:8]) or material[:2000],
    )


async def generate_note(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    study_session_id: UUID | None = None,
) -> Note:
    context = db.scalar(
        select(LearningContext).where(
            LearningContext.id == context_id, LearningContext.owner_id == owner_id
        )
    )
    if context is None:
        raise ValidationError("Learning context not found")
    material = _note_material(
        db, owner_id=owner_id, context_id=context_id, study_session_id=study_session_id
    )
    if not material:
        raise ValidationError("No study material or conversation to generate from")

    settings = get_settings()
    if settings.groq_api_key:
        try:
            provider = LiteLLMGroqProvider(api_key=settings.groq_api_key, model=settings.llm_model)
            prompt = (
                "Write concise, factual study notes grounded only in the supplied material. "
                'Return JSON matching the schema: {"title": "...", "body": "..."}. '
                "The body should be clean prose or short sections.\n\nMaterial:\n" + material
            )
            draft = await provider.generate_structured(prompt=prompt, schema=NoteDraftSchema)
        except Exception:
            draft = _deterministic_draft(material, context.title)
    else:
        draft = _deterministic_draft(material, context.title)

    sources = []
    if study_session_id is None:
        for chunk in context_chunks(db, owner_id=owner_id, context_id=context_id)[:5]:
            sources.append({"title": f"Chunk {chunk.chunk_index + 1}"})
    return create_note(
        db,
        owner_id=owner_id,
        context_id=context_id,
        title=draft.title,
        body=draft.body,
        study_session_id=study_session_id,
        source_refs=sources,
    )


def review_note(
    db: Session, *, owner_id: UUID, note_id: UUID, outcome: str
) -> Note:
    note = get_owned_note(db, owner_id=owner_id, note_id=note_id)
    item = revision_item(db, owner_id=owner_id, note_id=note.id)
    if item is None:
        raise ValidationError("Note has no revision schedule")
    if outcome == "again":
        item.interval_days = 1
        item.state = "REVIEWING"
    else:
        current = item.interval_days
        next_interval = next(
            (value for value in REVIEW_INTERVALS if value > current),
            REVIEW_INTERVALS[-1],
        )
        item.interval_days = next_interval
        item.state = "MASTERED" if next_interval >= REVIEW_INTERVALS[-1] else "LEARNING"
    item.last_outcome = outcome.upper()
    item.next_review_at = _now() + timedelta(days=item.interval_days)
    db.add(item)
    db.commit()
    db.refresh(note)
    return note


def due_notes(
    db: Session, *, owner_id: UUID, context_id: UUID, now: datetime | None = None
) -> list[Note]:
    cutoff = now or _now()
    rows = db.execute(
        select(Note, RevisionItem)
        .join(RevisionItem, RevisionItem.note_id == Note.id)
        .where(
            Note.owner_id == owner_id,
            Note.context_id == context_id,
            RevisionItem.owner_id == owner_id,
            RevisionItem.next_review_at <= cutoff,
        )
        .order_by(RevisionItem.next_review_at)
    ).all()
    return [note for note, _item in rows]


def _pick_font(text: str) -> str:
    for char in text:
        codepoint = ord(char)
        if 0x4E00 <= codepoint <= 0x9FFF:
            return "STSong-Light"
        if 0x3040 <= codepoint <= 0x30FF:
            return "HeiseiMin-W3"
        if 0xAC00 <= codepoint <= 0xD7AF:
            return "HYSMyeongJo-Medium"
    return "Helvetica"


def build_note_pdf(note: Note) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    for font_name in ("STSong-Light", "HeiseiMin-W3", "HYSMyeongJo-Medium"):
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(font_name))
        except Exception:
            continue

    font = _pick_font(note.title + note.body)
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    title_style = ParagraphStyle(
        "NoteTitle", fontName=font, fontSize=18, leading=22, spaceAfter=10
    )
    body_style = ParagraphStyle("NoteBody", fontName=font, fontSize=11, leading=16, spaceAfter=8)
    small_style = ParagraphStyle("Small", fontName=font, fontSize=9, leading=12)
    story = [
        Paragraph(escape(note.title), title_style),
        Spacer(1, 6),
    ]
    for paragraph in note.body.split("\n\n"):
        story.append(Paragraph(escape(paragraph), body_style))
    if note.source_refs:
        story.append(Spacer(1, 10))
        story.append(
            Paragraph(
                "Sources",
                ParagraphStyle("Sources", fontName=font, fontSize=13, leading=16),
            )
        )
        for ref in note.source_refs:
            story.append(Paragraph(f"• {escape(str(ref.get('title', '')))}", small_style))
    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            f"Generated by ARIA · {datetime.now(UTC).strftime('%Y-%m-%d')}",
            small_style,
        )
    )
    document.build(story)
    return buffer.getvalue()
