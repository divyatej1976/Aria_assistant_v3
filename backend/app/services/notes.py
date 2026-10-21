
"""Learner notes: CRUD, generation, spaced revision, and PDF export."""

import io
import logging
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID
from xml.sax.saxutils import escape

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.registry import get_llm_provider_for_owner
from app.assessment.schema import NoteDraftSchema
from app.core.errors import ValidationError
from app.db.models import (
    Concept,
    ConversationMessage,
    LearningContext,
    Note,
    RevisionItem,
    StudySession,
)
from app.services.audio import delete_artifacts_for_source as delete_audio_artifacts
from app.services.concepts import context_chunks
from app.services.contexts import get_owned_context, get_owned_related

REVIEW_INTERVALS = [1, 3, 7, 14, 30]


logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def get_owned_note(db: Session, *, owner_id: UUID, note_id: UUID) -> Note:
    note = db.scalar(
        select(Note).where(Note.id == note_id, Note.owner_id == owner_id)
    )
    if note is None:
        raise ValidationError("Note not found")
    return note


def list_notes(
    db: Session, *, owner_id: UUID, context_id: UUID, limit: int = 100
) -> list[Note]:
    return list(
        db.scalars(
            select(Note)
            .where(Note.owner_id == owner_id, Note.context_id == context_id)
            .order_by(Note.created_at.desc())
            .limit(limit)
        )
    )


def revision_items_for(
    db: Session, *, owner_id: UUID, note_ids: list[UUID]
) -> dict[UUID, RevisionItem]:
    """Batch-load revision items for many notes in one query (avoids N+1)."""
    if not note_ids:
        return {}
    rows = db.scalars(
        select(RevisionItem).where(
            RevisionItem.owner_id == owner_id, RevisionItem.note_id.in_(note_ids)
        )
    ).all()
    return {row.note_id: row for row in rows}


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
    get_owned_context(db, owner_id=owner_id, context_id=context_id)
    if concept_id is not None:
        get_owned_related(db, Concept, owner_id=owner_id, context_id=context_id,
                          related_id=concept_id, label="Concept")
    if study_session_id is not None:
        get_owned_related(db, StudySession, owner_id=owner_id, context_id=context_id,
                          related_id=study_session_id, label="Study session")
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
    delete_audio_artifacts(db, owner_id=owner_id, source_type="NOTE", source_id=note.id)
    db.delete(note)
    db.commit()


def _note_material(
    db: Session, *, owner_id: UUID, context_id: UUID, study_session_id: UUID | None
) -> str:
    if study_session_id is not None:
        session = db.scalar(select(StudySession).where(
            StudySession.id == study_session_id,
            StudySession.owner_id == owner_id,
            StudySession.context_id == context_id,
        ))
        if session is None:
            raise ValidationError("Study session does not belong to this subject")
        messages = db.scalars(
            select(ConversationMessage)
            .where(
                ConversationMessage.study_session_id == study_session_id,
                ConversationMessage.owner_id == owner_id,
            )
            .order_by(ConversationMessage.position)
        ).all()
        lines = [
            f"{'Learner' if message.role == 'user' else 'ARIA'}: {message.content.strip()}"
            for message in messages if message.content.strip() and not message.action
        ]
        return "\n\n".join(lines) if lines else ""
    chunks = context_chunks(db, owner_id=owner_id, context_id=context_id)
    return "\n\n".join(
        f"[{index + 1}] {chunk.content[:400]}" for index, chunk in enumerate(chunks[:12])
    )


def _deterministic_draft(material: str, context_title: str, chat_title: str | None = None) -> NoteDraftSchema:
    """Offline layout: one topic heading per answer, never the raw question."""
    from app.services.study import topic_title

    sections: list[str] = []
    question = ""
    for block in material.split("\n\n"):
        if block.startswith("Learner: "):
            question = block.removeprefix("Learner: ").strip()
        elif block.startswith("ARIA: "):
            heading = topic_title(question) if question else "Notes"
            sections.append(f"## {heading}\n\n{block.removeprefix('ARIA: ').strip()}")
            question = ""
        elif block.strip():
            sections.append(block.strip())
    return NoteDraftSchema(
        title=f"{chat_title or context_title} — Study notes",
        body="\n\n".join(sections) or material[:4000],
    )


NOTES_SYSTEM = (
    "You turn tutoring conversations and study material into clean revision notes. "
    "Write in Markdown like a textbook revision sheet. Never mention the conversation, "
    "the learner, the tutor or ARIA."
)
NOTES_PROMPT = (
    "Write study notes from the material below.\n"
    "- First line: '# ' and a specific title.\n"
    "- One '## ' section per topic, in a logical teaching order (not the order things were asked).\n"
    "- In each section: a short plain-language explanation of the idea and why it matters, key "
    "definitions in **bold**, bullet points of the facts to remember, and a worked example "
    "(a code block where it fits). Use '### ' sub-headings when a topic has parts.\n"
    "- Rewrite in your own structure: do not copy answer labels such as 'Direct answer' or "
    "'Intuition', and do not answer the questions one by one.\n"
    "- Add a '## Common mistakes' section if any came up.\n"
    "- End with '## Summary': 4-6 bullets.\n"
    "Keep every fact from the material; do not invent new ones.\n\nMaterial:\n{material}"
)


def _markdown_note(text: str, fallback_title: str) -> NoteDraftSchema:
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("# "):
        return NoteDraftSchema(title=lines[0][2:].strip()[:200] or fallback_title,
                               body="\n".join(lines[1:]).strip())
    return NoteDraftSchema(title=fallback_title, body=text.strip())


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
    chat_title = db.scalar(select(StudySession.title).where(
        StudySession.id == study_session_id, StudySession.owner_id == owner_id)) if study_session_id else None

    provider = get_llm_provider_for_owner(db, owner_id=owner_id)
    if provider is not None:
        try:
            if len(material) > 24_000:
                from app.services.condense import condense

                # Long chats are condensed in full, so early topics are not lost.
                material = await condense(provider, title=context.title, text=material, fits=20_000)
            from app.services.condense import generate_with_retry

            draft = _markdown_note(
                await generate_with_retry(provider, system=NOTES_SYSTEM, user=NOTES_PROMPT.format(material=material),
                                          prompt_version="note_draft:3"),
                f"{chat_title or context.title} — Study notes",
            )
            if not draft.body:
                raise ValueError("empty notes")
        except Exception:
            logger.warning("note generation fell back to the offline layout", exc_info=True)
            draft = _deterministic_draft(material, context.title, chat_title)
    else:
        draft = _deterministic_draft(material, context.title, chat_title)

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


# Characters models often emit that the built-in PDF fonts cannot draw (they print as black boxes).
_PDF_CHARS = str.maketrans({
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2015": "\u2014", "\u2212": "-",
    "\u00a0": " ", "\u2009": " ", "\u200a": " ", "\u202f": " ", "\u2007": " ", "\u200b": "",
    "\u2192": "->", "\u2190": "<-", "\u2194": "<->", "\u21d2": "=>", "\u21d4": "<=>",
    "\u2264": "<=", "\u2265": ">=", "\u2260": "!=", "\u2248": "~", "\u221e": "infinity",
    "\u2713": "(yes)", "\u2714": "(yes)", "\u2717": "(no)", "\u2718": "(no)",
})


def pdf_safe(text: str) -> str:
    """Map symbols the standard font lacks to plain equivalents; keep everything it can draw."""
    import unicodedata

    out = []
    for char in text.translate(_PDF_CHARS):
        try:
            char.encode("cp1252")
            out.append(char)
        except UnicodeEncodeError:
            ascii_form = unicodedata.normalize("NFKD", char).encode("ascii", "ignore").decode()
            out.append(ascii_form or char)
    return "".join(out)


def _inline(text: str) -> str:
    """Escape, then keep **bold**, *italic* and `code` as reportlab markup."""
    html = escape(text)
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    html = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<i>\1</i>", html)
    return re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', html)


def _markdown_flowables(body: str, *, font: str, body_style) -> list:
    """The small Markdown subset generated notes use: headings, bullets, code, paragraphs."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Preformatted

    h2 = ParagraphStyle("NoteH2", parent=body_style, fontSize=14, leading=18, spaceBefore=10, spaceAfter=6)
    h3 = ParagraphStyle("NoteH3", parent=body_style, fontSize=12, leading=16, spaceBefore=6, spaceAfter=4)
    bullet = ParagraphStyle("NoteBullet", parent=body_style, leftIndent=14, bulletIndent=4, spaceAfter=3)
    code = ParagraphStyle("NoteCode", fontName="Courier", fontSize=9, leading=12, leftIndent=8,
                          backColor="#f2f4f7", borderPadding=6, spaceBefore=4, spaceAfter=8)
    out: list = []
    paragraph: list[str] = []
    code_lines: list[str] | None = None

    def flush() -> None:
        if paragraph:
            out.append(Paragraph(_inline(" ".join(paragraph)), body_style))
            paragraph.clear()

    for raw in body.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            if code_lines is None:
                flush()
                code_lines = []
            else:
                out.append(Preformatted("\n".join(code_lines), code))
                code_lines = None
            continue
        if code_lines is not None:
            code_lines.append(line)
        elif not line.strip():
            flush()
        elif line.startswith(("## ", "# ")):
            flush()
            out.append(Paragraph(_inline(line.lstrip("#").strip()), h2))
        elif line.startswith("### "):
            flush()
            out.append(Paragraph(_inline(line[4:].strip()), h3))
        elif re.match(r"^\s*([-*•]|\d+\.)\s+", line):
            flush()
            out.append(Paragraph(_inline(re.sub(r"^\s*([-*•]|\d+\.)\s+", "", line)), bullet, bulletText="•"))
        else:
            paragraph.append(line.strip())
    flush()
    if code_lines:
        out.append(Preformatted("\n".join(code_lines), code))
    return out


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
    # CJK fonts draw these symbols; the standard font needs plain equivalents.
    plain = font == "Helvetica"
    note_title, note_body = (pdf_safe(note.title), pdf_safe(note.body)) if plain else (note.title, note.body)
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
        Paragraph(escape(note_title), title_style),
        Spacer(1, 6),
    ]
    story.extend(_markdown_flowables(note_body, font=font, body_style=body_style))
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
