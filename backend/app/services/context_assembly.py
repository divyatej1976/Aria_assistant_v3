"""Context Assembly pipeline.

Gathers the focused, explainable context package ARIA feeds an AI model:
recent conversation history, relevant learner state, relevant evidence, and
the retrieved resource chunks. Resource and conversation text are always
treated as data and never influence the system instruction.
"""

from dataclasses import dataclass, replace
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers import RetrievedChunk
from app.db.models import (
    Concept,
    ConversationMessage,
    Evidence,
    LearnerConceptState,
)
from app.services.learner_state import (
    STATE_DEVELOPING,
    STATE_NEEDS_REVIEW,
    STATE_SUPPORTED,
    STATE_UNTESTED,
)

STUDY_SYSTEM_PROMPT = (
    "You are ARIA, an expert, supportive AI learning companion and tutor.\n\n"
    "RESPONSE STRUCTURE & SOURCE PROVENANCE RULES:\n"
    "1. WHEN STUDY MATERIAL IS PROVIDED (under 'Study material:'):\n"
    "   You MUST format your answer in this exact order with these exact markdown section headings:\n"
    "   - ### 📄 Information from Document: [Source Title]\n"
    "     Structure and explain the information provided in the uploaded document with clear bullet points, "
    "numbered steps, or tables. State explicitly: '*This information is directly from your uploaded document.*'\n"
    "   - ### 💡 Extra Info (ARIA Enhancement)\n"
    "     Under this section, provide supplementary information that is OUT of the document to know more, "
    "such as practical real-world applications, analogies, or best practices. "
    "State explicitly: '*(Out of document — extra information provided by ARIA to enrich your understanding)*'\n"
    "   - Footer: Always end with:\n"
    "     **Source Document:** [Source Title]\n\n"
    "2. WHEN NO STUDY MATERIAL IS PROVIDED:\n"
    "   - Answer thoroughly, clearly, and engagingly using your general knowledge with step-by-step explanations, "
    "bullet points, and code snippets where appropriate.\n"
    "   - Footer: Always end with:\n"
    "     **Source:** ARIA Knowledge Base (No document attached)\n\n"
    "3. LEARNER PATTERN & ADAPTIVE SELF-LOOP:\n"
    "   - Actively analyze the learner's ongoing interaction pattern in the 'Conversation so "
    "far:' and 'Learner state:' "
    "(e.g., whether they prefer code over theory, ask for simpler beginner explanations, or "
    "dive deep into mechanics).\n"
    "   - Seamlessly adapt your explanation style, level of detail, and examples to match their "
    "learning pattern in this self-improving loop.\n\n"
    "4. TONE & FORMATTING:\n"
    "   - Welcoming, encouraging, concise, and pedagogical.\n"
    "   - Keep both sections clear and focused so the learner can quickly grasp both the "
    "document facts and the extra knowledge."
)


@dataclass(frozen=True)
class ContextPackage:
    recent_messages: list[dict]
    relevant_states: list[dict]
    recent_evidence: list[dict]
    retrieved_chunks: list[RetrievedChunk]


def pack_study_context(
    sources: list[RetrievedChunk], *, max_chars: int = 4000, per_chunk: int | None = None
) -> tuple[str, list[RetrievedChunk]]:
    """Return rendered material and exactly the source excerpts it contains."""
    parts: list[str] = []
    included: list[RetrievedChunk] = []
    seen: set[str] = set()
    used = 0
    for source in sources:
        if source.score <= 0 or not source.content.strip():
            continue
        content = source.content[:per_chunk] if per_chunk is not None else source.content
        key = " ".join(content.lower().split())[:200]
        if key in seen:
            continue
        seen.add(key)
        prefix = f"[{source.source_title}] "
        separator = 2 if parts else 0
        available = max_chars - used - separator - len(prefix)
        if available <= 0:
            break
        excerpt = content[:available]
        if not excerpt.strip():
            continue
        block = prefix + excerpt
        parts.append(block)
        included.append(replace(source, content=excerpt))
        used += separator + len(block)
        if len(excerpt) < len(content):
            break
    return "\n\n".join(parts), included


def build_study_context(
    sources: list[RetrievedChunk], *, max_chars: int = 4000, per_chunk: int | None = None
) -> str:
    return pack_study_context(sources, max_chars=max_chars, per_chunk=per_chunk)[0]


def build_study_messages(*, question: str, context_text: str) -> tuple[str, str]:
    """Build (system, user) prompt messages.

    The system instruction is a constant; the learner question and the source
    material are placed only in the user message.
    """
    return STUDY_SYSTEM_PROMPT, f"Study material:\n{context_text}\n\nLearner question: {question}"


def recent_messages(
    db: Session, *, owner_id: UUID, session_id: UUID | None, limit: int = 10
) -> list[dict]:
    if session_id is None:
        return []
    rows = db.scalars(
        select(ConversationMessage)
        .where(
            ConversationMessage.study_session_id == session_id,
            ConversationMessage.owner_id == owner_id,
        )
        .order_by(
            ConversationMessage.position.desc(), ConversationMessage.created_at.desc()
        )
        .limit(limit)
    ).all()
    return [{"role": message.role, "content": message.content} for message in reversed(rows)]


def _state_priority(state: str) -> int:
    return {STATE_NEEDS_REVIEW: 0, STATE_DEVELOPING: 1, STATE_SUPPORTED: 2}.get(state, 9)


def relevant_learner_states(
    db: Session, *, owner_id: UUID, context_id: UUID, limit: int = 6
) -> list[dict]:
    rows = db.execute(
        select(LearnerConceptState, Concept)
        .join(Concept, Concept.id == LearnerConceptState.concept_id)
        .where(
            LearnerConceptState.owner_id == owner_id,
            Concept.context_id == context_id,
        )
    ).all()
    states = [
        {"concept_name": concept.name, "state": learner_state.state}
        for learner_state, concept in rows
        if learner_state.state != STATE_UNTESTED
    ]
    states.sort(key=lambda item: _state_priority(item["state"]))
    return states[:limit]


def recent_evidence(
    db: Session, *, owner_id: UUID, context_id: UUID, limit: int = 8
) -> list[dict]:
    rows = db.execute(
        select(Evidence, Concept)
        .join(Concept, Concept.id == Evidence.concept_id)
        .where(
            Evidence.owner_id == owner_id,
            Evidence.valid.is_(True),
            Concept.context_id == context_id,
        )
        .order_by(Evidence.created_at.desc())
        .limit(limit)
    ).all()
    return [{"concept_name": concept.name, "signal": evidence.signal} for evidence, concept in rows]


def assemble_context(
    db: Session,
    *,
    owner_id: UUID,
    context_id: UUID,
    session_id: UUID | None,
    sources: list[RetrievedChunk],
) -> ContextPackage:
    return ContextPackage(
        recent_messages=recent_messages(db, owner_id=owner_id, session_id=session_id),
        relevant_states=relevant_learner_states(db, owner_id=owner_id, context_id=context_id),
        recent_evidence=recent_evidence(db, owner_id=owner_id, context_id=context_id),
        retrieved_chunks=sources,
    )


def _human_state(state: str) -> str:
    return state.replace("_", " ").title()


def build_prompt(
    question: str, package: ContextPackage, *, max_chars: int = 4000
) -> tuple[str, str]:
    """Build the (system, user) prompt from an assembled context package."""
    sections: list[str] = []
    if package.relevant_states:
        state_line = "; ".join(
            f"{item['concept_name']} ({_human_state(item['state'])})"
            for item in package.relevant_states[:3]
        )
        sections.append(f"Learner state: {state_line}")
    history = package.recent_messages[-6:]
    if history:
        lines = ["Conversation so far:"]
        for message in history:
            role = "Learner" if message["role"] == "user" else "ARIA"
            lines.append(f"{role}: {message['content'][:300]}")
        sections.append("\n".join(lines))
    context_text = build_study_context(
        package.retrieved_chunks, max_chars=max_chars, per_chunk=1200
    )
    if context_text:
        sections.append(f"Study material:\n{context_text}")
    sections.append(f"Learner question: {question}")
    return STUDY_SYSTEM_PROMPT, "\n\n".join(sections)
