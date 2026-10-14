"""A bounded next-day review plan from assessed weaknesses, never chat activity."""

from datetime import UTC, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Assessment, LearningContext, PlannedTask, Roadmap
from app.services.learner_state import context_states_with_concepts
from app.services.progress import learner_timezone
from app.services.roadmap import sync_roadmap_ticks


def apply_daily_review_results(
    db: Session, *, owner_id: UUID, assessment_id: UUID, evaluation_id: UUID
) -> None:
    assessment = db.scalar(select(Assessment).where(
        Assessment.id == assessment_id, Assessment.owner_id == owner_id,
    ))
    if assessment is None or assessment.mode != "DAILY_REVIEW":
        return
    # Serialize plan creation across concurrent attempts in the same subject.
    db.scalar(select(LearningContext).where(
        LearningContext.id == assessment.context_id, LearningContext.owner_id == owner_id,
    ).with_for_update())
    db.refresh(assessment)
    applied = set(assessment.configuration.get("review_applied_evaluations", []))
    if str(evaluation_id) in applied:
        # Replaying a completed submission must not recreate a review task the
        # learner subsequently completed or deleted.
        db.commit()
        return
    pairs = context_states_with_concepts(db, owner_id=owner_id, context_id=assessment.context_id)
    eligible = set(assessment.configuration.get("concept_ids", []))
    weaknesses = [(state, concept) for state, concept in pairs
                  if str(concept.id) in eligible and state.state in {"NEEDS_REVIEW", "DEVELOPING"}]
    weaknesses.sort(key=lambda pair: (pair[0].state != "NEEDS_REVIEW", pair[0].confidence, pair[1].name))
    task_ids = dict(assessment.configuration.get("review_task_ids", {}))
    automatic_tasks: dict[str, set[UUID]] = {}
    for previous in db.scalars(select(Assessment).where(
        Assessment.owner_id == owner_id, Assessment.context_id == assessment.context_id,
        Assessment.mode == "DAILY_REVIEW",
    )):
        for concept_id, task_id in previous.configuration.get("review_task_ids", {}).items():
            automatic_tasks.setdefault(concept_id, set()).add(UUID(task_id))
    for state, concept in pairs:
        ids = automatic_tasks.get(str(concept.id), set())
        if state.state != "SUPPORTED" or not ids:
            continue
        tasks = db.scalars(select(PlannedTask).where(
            PlannedTask.id.in_(ids), PlannedTask.owner_id == owner_id,
            PlannedTask.context_id == assessment.context_id,
        ))
        for task in tasks:
            if task.status == "PENDING":
                task.status = "DONE"
                task.completed_at = datetime.now(UTC)
    timezone = learner_timezone(db, owner_id=owner_id)
    tomorrow = datetime.now(timezone).date() + timedelta(days=1)
    due = datetime.combine(tomorrow, time(9), tzinfo=timezone).astimezone(UTC)
    for _state, concept in weaknesses[:3]:
        title = ("Review: " + concept.name)[:255]
        pending = db.scalar(select(PlannedTask).where(
            PlannedTask.owner_id == owner_id, PlannedTask.context_id == assessment.context_id,
            PlannedTask.title == title, PlannedTask.status == "PENDING",
        ))
        if pending is None:
            task = PlannedTask(owner_id=owner_id, context_id=assessment.context_id,
                               title=title, due_at=due, status="PENDING")
            db.add(task)
            db.flush()
            task_ids[str(concept.id)] = str(task.id)
        elif pending.id in automatic_tasks.get(str(concept.id), set()):
            task_ids[str(concept.id)] = str(pending.id)
    applied.add(str(evaluation_id))
    assessment.configuration = {
        **assessment.configuration, "review_task_ids": task_ids,
        "review_applied_evaluations": sorted(applied),
    }
    db.commit()
    for roadmap in db.scalars(select(Roadmap).where(
        Roadmap.owner_id == owner_id, Roadmap.context_id == assessment.context_id,
    )):
        sync_roadmap_ticks(db, owner_id=owner_id, roadmap=roadmap)
