"""Learner memory services: preferences, durable-memory summary, message
deletion, and manual concept prerequisite links."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db.models import (
    Concept,
    ConceptRelation,
    ConversationMessage,
    Evidence,
    LearnerConceptState,
    LearnerPreference,
)
from app.services.contexts import get_owned_context, get_owned_related
from app.services.learner_state import STATE_DEVELOPING, STATE_NEEDS_REVIEW, STATE_SUPPORTED

WEAK_STATES = (STATE_NEEDS_REVIEW, STATE_DEVELOPING)


def list_preferences(db: Session, *, owner_id: UUID) -> list[LearnerPreference]:
    return list(
        db.scalars(
            select(LearnerPreference)
            .where(LearnerPreference.owner_id == owner_id)
            .order_by(LearnerPreference.key)
        )
    )


def upsert_preference(
    db: Session, *, owner_id: UUID, key: str, value: str
) -> LearnerPreference:
    preference = db.scalar(
        select(LearnerPreference).where(
            LearnerPreference.owner_id == owner_id, LearnerPreference.key == key
        )
    )
    if preference is None:
        preference = LearnerPreference(owner_id=owner_id, key=key, value=value)
        db.add(preference)
    else:
        preference.value = value
        db.add(preference)
    db.commit()
    db.refresh(preference)
    return preference


def delete_preference(db: Session, *, owner_id: UUID, key: str) -> bool:
    result = db.execute(
        delete(LearnerPreference).where(
            LearnerPreference.owner_id == owner_id, LearnerPreference.key == key
        )
    )
    db.commit()
    return result.rowcount > 0


def memory_summary(db: Session, *, owner_id: UUID) -> dict[str, object]:
    preferences = [
        {"key": preference.key, "value": preference.value}
        for preference in list_preferences(db, owner_id=owner_id)
    ]
    concepts = db.scalar(
        select(func.count(Concept.id)).where(Concept.owner_id == owner_id)
    )
    weak = db.scalar(
        select(func.count(LearnerConceptState.id))
        .join(Concept, Concept.id == LearnerConceptState.concept_id)
        .where(
            LearnerConceptState.owner_id == owner_id,
            LearnerConceptState.state.in_(WEAK_STATES),
        )
    )
    supported = db.scalar(
        select(func.count(LearnerConceptState.id))
        .join(Concept, Concept.id == LearnerConceptState.concept_id)
        .where(
            LearnerConceptState.owner_id == owner_id,
            LearnerConceptState.state == STATE_SUPPORTED,
        )
    )
    evidence_count = db.scalar(
        select(func.count(Evidence.id)).where(
            Evidence.owner_id == owner_id, Evidence.valid.is_(True)
        )
    )
    message_count = db.scalar(
        select(func.count(ConversationMessage.id)).where(
            ConversationMessage.owner_id == owner_id
        )
    )
    return {
        "preferences": preferences,
        "concepts": concepts or 0,
        "weak_concepts": weak or 0,
        "supported_concepts": supported or 0,
        "evidence_count": evidence_count or 0,
        "message_count": message_count or 0,
    }


def delete_message(
    db: Session, *, owner_id: UUID, session_id: UUID, message_id: UUID
) -> bool:
    from app.db.models import BrainAction
    db.execute(delete(BrainAction).where(BrainAction.id == message_id,
        BrainAction.owner_id == owner_id, BrainAction.session_id == session_id))
    result = db.execute(
        delete(ConversationMessage).where(
            ConversationMessage.id == message_id,
            ConversationMessage.owner_id == owner_id,
            ConversationMessage.study_session_id == session_id,
        )
    )
    db.commit()
    return result.rowcount > 0


def _owned_concept(db: Session, *, owner_id: UUID, concept_id: UUID) -> Concept | None:
    return db.scalar(
        select(Concept).where(Concept.id == concept_id, Concept.owner_id == owner_id)
    )


def list_prerequisites(
    db: Session, *, owner_id: UUID, concept_id: UUID
) -> list[dict[str, object]]:
    rows = db.execute(
        select(ConceptRelation, Concept)
        .join(Concept, Concept.id == ConceptRelation.prerequisite_concept_id)
        .where(
            ConceptRelation.owner_id == owner_id,
            ConceptRelation.concept_id == concept_id,
        )
        .order_by(Concept.name)
    ).all()
    return [
        {
            "concept_id": str(concept_id),
            "prerequisite_concept_id": str(concept.id),
            "prerequisite_name": concept.name,
        }
        for _relation, concept in rows
    ]


def add_prerequisite(
    db: Session, *, owner_id: UUID, concept_id: UUID, prerequisite_concept_id: UUID
) -> None:
    if concept_id == prerequisite_concept_id:
        raise ValidationError("A concept cannot be its own prerequisite")
    concept = _owned_concept(db, owner_id=owner_id, concept_id=concept_id)
    if concept is None:
        raise ValidationError("Concept not found")
    get_owned_context(db, owner_id=owner_id, context_id=concept.context_id)
    get_owned_related(db, Concept, owner_id=owner_id, context_id=concept.context_id,
                      related_id=prerequisite_concept_id, label="Prerequisite concept")
    existing = db.scalar(
        select(ConceptRelation).where(
            ConceptRelation.owner_id == owner_id,
            ConceptRelation.concept_id == concept_id,
            ConceptRelation.prerequisite_concept_id == prerequisite_concept_id,
        )
    )
    if existing is None:
        db.add(
            ConceptRelation(
                owner_id=owner_id,
                concept_id=concept_id,
                prerequisite_concept_id=prerequisite_concept_id,
            )
        )
        db.commit()


def remove_prerequisite(
    db: Session, *, owner_id: UUID, concept_id: UUID, prerequisite_concept_id: UUID
) -> bool:
    result = db.execute(
        delete(ConceptRelation).where(
            ConceptRelation.owner_id == owner_id,
            ConceptRelation.concept_id == concept_id,
            ConceptRelation.prerequisite_concept_id == prerequisite_concept_id,
        )
    )
    db.commit()
    return result.rowcount > 0


def weak_prerequisite_names(
    db: Session, *, owner_id: UUID, concept_id: UUID
) -> list[str]:
    rows = db.execute(
        select(ConceptRelation, Concept, LearnerConceptState)
        .join(Concept, Concept.id == ConceptRelation.prerequisite_concept_id)
        .join(
            LearnerConceptState,
            LearnerConceptState.concept_id == ConceptRelation.prerequisite_concept_id,
        )
        .where(
            ConceptRelation.owner_id == owner_id,
            ConceptRelation.concept_id == concept_id,
            LearnerConceptState.owner_id == owner_id,
            LearnerConceptState.state.in_(WEAK_STATES),
        )
        .order_by(Concept.name)
    ).all()
    return [concept.name for _relation, concept, _state in rows]
