import logging
import re
from uuid import UUID

from pydantic import ValidationError as SchemaValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.prompts import get_prompt
from app.ai.registry import get_llm_provider_for_owner
from app.core.errors import ValidationError
from app.db.models import (
    Concept,
    LearnerConceptState,
    Roadmap,
    RoadmapMilestone,
)
from app.schemas.roadmap import (
    GeneratedMilestone,
    GeneratedPhase,
    GeneratedRoadmapTree,
    RoadmapCreateRequest,
    RoadmapMilestoneResponse,
    RoadmapResponse,
    RoadmapSummaryResponse,
    RoadmapTierResponse,
)
from app.services.contexts import get_owned_context

logger = logging.getLogger(__name__)

TIER_NAMES = ["Foundations", "Core Concepts", "Advanced Topics", "Mastery Track"]
TIER_ICONS = ["book", "target", "zap", "trophy"]


def _fallback_roadmap_tree(goal: str, level: str) -> GeneratedRoadmapTree:
    """An honest domain-neutral starter plan, not an invented expert curriculum."""
    clean_goal = goal.strip().rstrip(".") or goal.strip()
    stages = [
        ("Foundations", "Define the goal and starting point",
         "Identify what success means, what you already know, and reliable introductory material.",
         ["Fundamentals", "Terminology"]),
        ("Foundations", "Understand the essential ideas",
         "Study the key ideas and explain their meaning using examples from your chosen subject.",
         ["Core Concepts", "Concept Relationships"]),
        ("Core Concepts", "Work through guided examples",
         "Follow worked examples or demonstrations relevant to your goal, explaining each step.",
         ["Guided Practice", "Explanation"]),
        ("Core Concepts", "Practice independently",
         "Try new exercises without guidance and compare your work with trustworthy references.",
         ["Independent Practice", "Problem Solving"]),
        ("Advanced Topics", "Apply the ideas in a new situation",
         "Choose a realistic task, question, or project that uses the knowledge you are building.",
         ["Application", "Transfer"]),
        ("Advanced Topics", "Find and address knowledge gaps",
         "Assess your understanding, revisit mistakes, and strengthen the skills that need review.",
         ["Self Assessment", "Error Analysis"]),
        ("Mastery Track", "Demonstrate the learning goal",
         "Explain or demonstrate your result and gather feedback against your original success criteria.",
         ["Demonstration", "Reflection"]),
    ]
    # "master microservices" -> "Microservices": milestone names lead with the subject, not the verb.
    subject = re.sub(r"^(?:i want to |to )?(?:master|learn|understand|study|get (?:good|better) at|become good at)\s+",
                     "", clean_goal, flags=re.I).strip() or clean_goal
    subject = subject[:1].upper() + subject[1:]
    phases: dict[str, list[GeneratedMilestone]] = {}
    previous = None
    for phase, title, description, skills in stages:
        named_title = f"{subject[:200 - len(title) - 2]}: {title}"
        phases.setdefault(phase, []).append(GeneratedMilestone(
            title=named_title,
            description=(
                f"Offline starter plan for {clean_goal}. {description} "
                "This is a general learning structure; add subject-specific skills from your material."
            ),
            key_skills=skills,
            prerequisites=[previous] if previous else [],
            outcome=f"You can {title[0].lower() + title[1:]}.",
            effort_hours=3,
            activity="Study it with ARIA in Learn, asking for examples as you go.",
            check="Take a Quick check quiz from the chat when you feel ready.",
        ))
        previous = named_title
    return GeneratedRoadmapTree(
        goal=clean_goal, level=level,
        phases=[GeneratedPhase(phase_name=name, milestones=milestones) for name, milestones in phases.items()],
    )


async def generate_roadmap_tree(
    goal: str,
    level: str = "Beginner",
    target_date: str | None = None,
    *,
    db: Session | None = None,
    owner_id: UUID | None = None,
) -> GeneratedRoadmapTree:
    """Generate a goal-oriented curriculum tree using the LLM with deterministic fallback."""
    provider = None
    if db is not None and owner_id is not None:
        provider = get_llm_provider_for_owner(db, owner_id=owner_id)
    if provider is None:
        from app.ai.registry import get_llm_provider

        provider = get_llm_provider()

    fallback_reason = "provider_unavailable"
    if provider is not None:
        fallback_reason = "provider_failed"
        try:
            prompt_version = get_prompt("roadmap_tree_generation")
            prompt = prompt_version.render(
                goal=goal,
                level=level,
                target_date=target_date or "Self-paced",
            )
            parsed = await provider.generate_structured(
                prompt=prompt,
                schema=GeneratedRoadmapTree,
                prompt_version=prompt_version.label(),
            )
            fallback_reason = "invalid_output"
            # Revalidate even provider adapters that return constructed/mutated
            # model instances without running Pydantic validation.
            validated = GeneratedRoadmapTree.model_validate(
                parsed.model_dump() if isinstance(parsed, GeneratedRoadmapTree) else parsed
            )
            if not _same_goal(goal, validated.goal):
                raise ValueError("Provider changed the requested learning goal")
            if validated.level != level:
                raise ValueError("Provider changed the requested learning level")
            # Keep the learner's own wording; the provider may rephrase it.
            validated.goal = goal
            validated._generation_mode = "ai"
            return validated
        except Exception:
            logger.warning("roadmap generation fell back fallback_reason=%s", fallback_reason, exc_info=True)

    fallback = _fallback_roadmap_tree(goal, level)
    fallback._generation_mode = "starter"
    fallback._fallback_reason = fallback_reason
    return fallback


def _same_goal(requested: str, generated: str) -> bool:
    """Tolerate rephrasing ("Learn SQL" -> "Learning SQL fundamentals") but
    not a different subject: most of the requested words must survive."""
    wanted = {_stem(w) for w in _normalize(requested)}
    if not wanted:
        return True
    got = {_stem(w) for w in _normalize(generated)}
    return len(wanted & got) * 2 >= len(wanted)


def _normalize(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _stem(word: str) -> str:
    w = word.lower()
    for suffix in ("ing", "tions", "tion", "ies", "es", "s", "ed"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[:-len(suffix)]
    return w


def sync_roadmap_ticks(
    db: Session, *, owner_id: UUID, roadmap: Roadmap,
    milestones=None, state_rows=None, commit: bool = True,
) -> None:
    """Recompute completion from every required skill in the roadmap's subject."""
    if milestones is None:
        milestones = list(db.scalars(
            select(RoadmapMilestone)
            .where(RoadmapMilestone.owner_id == owner_id, RoadmapMilestone.roadmap_id == roadmap.id)
            .order_by(RoadmapMilestone.phase_order, RoadmapMilestone.order_index)
        ))
    if not milestones:
        return

    def key(value: str) -> str:
        return " ".join(re.findall(r"\w+", value.casefold()))

    # Account-wide matching is deliberately disabled: a subject must be selected
    # before evidence can establish completion of its curriculum.
    states = {}
    if roadmap.context_id is not None:
        rows = state_rows if state_rows is not None else db.execute(
            select(LearnerConceptState, Concept.name)
            .join(Concept, Concept.id == LearnerConceptState.concept_id)
            .where(
                LearnerConceptState.owner_id == owner_id,
                Concept.owner_id == owner_id,
                Concept.context_id == roadmap.context_id,
            )
            .order_by(LearnerConceptState.updated_at.desc())
        ).all()
        for state, name in rows:
            states.setdefault(key(name), state)

    requirements = {}
    evidence = {}
    eligible = {}
    by_title = {}
    for milestone in milestones:
        by_title.setdefault(key(milestone.title), []).append(milestone)
        skills = list(dict.fromkeys(key(skill) for skill in milestone.key_skills if key(skill)))
        # A milestone without explicit skills requires its exact named concept.
        requirements[milestone.id] = skills or [key(milestone.title)]
        def lookup_state(skill_name: str):
            st = states.get(skill_name)
            if st is not None:
                return st
            stemmed = _stem(skill_name)
            for k, s in states.items():
                if _stem(k) == stemmed:
                    return s
            return None

        evidence[milestone.id] = [lookup_state(skill) for skill in requirements[milestone.id]]
        eligible[milestone.id] = all(
            state is not None and state.state == "SUPPORTED" for state in evidence[milestone.id]
        )

    def completed(milestone, visiting: set) -> bool:
        if milestone.id in visiting or not eligible[milestone.id]:
            return False
        path = visiting | {milestone.id}
        for prerequisite in milestone.prerequisites:
            matches = by_title.get(key(prerequisite), [])
            if len(matches) != 1 or not completed(matches[0], path):
                return False
        return True

    for milestone in milestones:
        rows = evidence[milestone.id]
        covered = sum(state is not None and state.state == "SUPPORTED" for state in rows)
        milestone.confidence = min(state.confidence if state is not None else 0 for state in rows)
        if completed(milestone, set()):
            milestone.state = "SUPPORTED"
            milestone.reason = f"All {len(rows)} required skills and prerequisite milestones are supported."
        elif any(state is not None and state.state == "NEEDS_REVIEW" for state in rows):
            milestone.state = "NEEDS_REVIEW"
            milestone.reason = "Current evidence requires review of a required skill."
        elif covered:
            milestone.state = "DEVELOPING"
            milestone.reason = (
                "Required skills are supported; prerequisite milestones remain incomplete."
                if eligible[milestone.id]
                else f"{covered} of {len(rows)} required skills supported."
            )
        else:
            milestone.state = "NOT_STARTED"
            milestone.reason = (
                "Select a subject before tracking evidence-based completion."
                if roadmap.context_id is None
                else "No complete skill coverage yet. Study and assess the required concepts."
            )
    if commit:
        db.commit()


async def create_roadmap(
    db: Session,
    *,
    owner_id: UUID,
    goal: str,
    level: str = "Beginner",
    target_date: str | None = None,
    context_id: UUID | None = None,
    hours_per_week: int | None = None,
    focus: str | None = None,
) -> Roadmap:
    """Generate and persist a new goal-isolated roadmap."""
    try:
        validated = RoadmapCreateRequest(goal=goal, level=level, target_date=target_date,
                                         hours_per_week=hours_per_week, focus=focus, context_id=context_id)
    except SchemaValidationError as exc:
        raise ValidationError("Invalid roadmap goal, level, or target date") from exc
    goal, level, target_date = validated.goal, validated.level, validated.target_date
    if context_id is not None:
        get_owned_context(db, owner_id=owner_id, context_id=context_id)
    tree = await generate_roadmap_tree(
        goal=goal,
        level=level,
        target_date=_pace(target_date, validated.hours_per_week, validated.focus),
        db=db,
        owner_id=owner_id,
    )

    roadmap = Roadmap(
        owner_id=owner_id,
        context_id=context_id,
        goal=goal.strip(),
        level=level,
        target_date=target_date,
        hours_per_week=validated.hours_per_week,
        focus=validated.focus,
        status="ACTIVE",
        generation_mode=tree._generation_mode,
        fallback_reason=tree._fallback_reason,
    )
    db.add(roadmap)
    db.flush()
    _save_milestones(db, owner_id=owner_id, roadmap=roadmap, tree=tree)
    db.commit()
    db.refresh(roadmap)
    sync_roadmap_ticks(db, owner_id=owner_id, roadmap=roadmap)
    return roadmap


def _pace(target_date: str | None, hours_per_week: int | None, focus: str | None, request: str | None = None) -> str:
    """The timeframe line tells the generator how much the plan has to fit and what to stress."""
    pace = f"{target_date or 'Self-paced'}"
    if hours_per_week:
        pace += f" (about {hours_per_week} hours of study per week)"
    if focus and focus != "mixed":
        pace += f"; emphasise {focus}"
    if request:
        pace += f"; the learner asked to change the plan: {request}"
    return pace


def _save_milestones(db: Session, *, owner_id: UUID, roadmap: Roadmap, tree: GeneratedRoadmapTree) -> None:
    phase_order_map = {name: idx for idx, name in enumerate(TIER_NAMES)}
    order = 0
    for phase in tree.phases:
        for milestone in phase.milestones:
            db.add(RoadmapMilestone(
                owner_id=owner_id,
                roadmap_id=roadmap.id,
                phase_name=phase.phase_name,
                phase_order=phase_order_map.get(phase.phase_name, 0),
                title=milestone.title,
                description=milestone.description,
                key_skills=milestone.key_skills,
                prerequisites=milestone.prerequisites,
                details={key: value for key, value in {
                    "outcome": milestone.outcome, "effort_hours": milestone.effort_hours,
                    "activity": milestone.activity, "check": milestone.check,
                }.items() if value is not None},
                state="NOT_STARTED",
                confidence=0,
                reason="Not started yet.",
                order_index=order,
            ))
            order += 1


async def refine_roadmap(db: Session, *, owner_id: UUID, roadmap_id: UUID, instruction: str) -> Roadmap:
    """Rebuild the milestones from the original answers plus the learner's request.

    Progress is not lost: ticks come from quiz evidence and are re-synced afterwards.
    """
    roadmap = db.scalar(select(Roadmap).where(Roadmap.id == roadmap_id, Roadmap.owner_id == owner_id))
    if roadmap is None:
        raise ValidationError("Roadmap not found")
    tree = await generate_roadmap_tree(
        goal=roadmap.goal, level=roadmap.level,
        target_date=_pace(roadmap.target_date, roadmap.hours_per_week, roadmap.focus, instruction.strip()[:300]),
        db=db, owner_id=owner_id,
    )
    db.execute(delete(RoadmapMilestone).where(
        RoadmapMilestone.roadmap_id == roadmap.id, RoadmapMilestone.owner_id == owner_id,
    ))
    _save_milestones(db, owner_id=owner_id, roadmap=roadmap, tree=tree)
    roadmap.generation_mode = tree._generation_mode
    roadmap.fallback_reason = tree._fallback_reason
    db.commit()
    db.refresh(roadmap)
    sync_roadmap_ticks(db, owner_id=owner_id, roadmap=roadmap)
    return roadmap


def list_roadmaps(
    db: Session, *, owner_id: UUID, context_id: UUID | None = None
) -> list[RoadmapSummaryResponse]:
    """List all roadmaps for learner, optionally filtered by context."""
    query = select(Roadmap).where(
        Roadmap.owner_id == owner_id,
        Roadmap.status == "ACTIVE",
    )
    if context_id is not None:
        query = query.where(Roadmap.context_id == context_id)
    query = query.order_by(Roadmap.created_at.desc())

    roadmaps = list(db.scalars(query))
    summaries: list[RoadmapSummaryResponse] = []
    if not roadmaps:
        return summaries
    milestones_by_roadmap = {r.id: [] for r in roadmaps}
    for milestone in db.scalars(
        select(RoadmapMilestone).where(
            RoadmapMilestone.owner_id == owner_id,
            RoadmapMilestone.roadmap_id.in_(milestones_by_roadmap),
        ).order_by(RoadmapMilestone.phase_order, RoadmapMilestone.order_index)
    ):
        milestones_by_roadmap[milestone.roadmap_id].append(milestone)
    contexts = {r.context_id for r in roadmaps if r.context_id is not None}
    states_by_context = {cid: [] for cid in contexts}
    if contexts:
        for state, name, cid in db.execute(
            select(LearnerConceptState, Concept.name, Concept.context_id)
            .join(Concept, Concept.id == LearnerConceptState.concept_id)
            .where(LearnerConceptState.owner_id == owner_id, Concept.owner_id == owner_id,
                   Concept.context_id.in_(contexts))
            .order_by(LearnerConceptState.updated_at.desc())
        ):
            states_by_context[cid].append((state, name))

    for r in roadmaps:
        milestones = milestones_by_roadmap[r.id]
        sync_roadmap_ticks(
            db, owner_id=owner_id, roadmap=r, milestones=milestones,
            state_rows=states_by_context.get(r.context_id, []), commit=False,
        )
        total = len(milestones)
        done = sum(1 for m in milestones if m.state == "SUPPORTED")
        summaries.append(
            RoadmapSummaryResponse(
                id=str(r.id),
                goal=r.goal,
                level=r.level,
                target_date=r.target_date,
                hours_per_week=r.hours_per_week,
                status=r.status,
                generation_mode=r.generation_mode,
                fallback_reason=r.fallback_reason,
                created_at=r.created_at.isoformat(),
                total=total,
                done=done,
            )
        )
    db.commit()
    return summaries


def get_roadmap(db: Session, *, owner_id: UUID, roadmap_id: UUID) -> RoadmapResponse:
    """Retrieve a roadmap with tiered milestones organized for the UI."""
    roadmap = db.scalar(
        select(Roadmap).where(
            Roadmap.id == roadmap_id,
            Roadmap.owner_id == owner_id,
        )
    )
    if roadmap is None:
        raise ValidationError("Roadmap not found")

    sync_roadmap_ticks(db, owner_id=owner_id, roadmap=roadmap)

    milestones = list(
        db.scalars(
            select(RoadmapMilestone)
            .where(
                RoadmapMilestone.owner_id == owner_id,
                RoadmapMilestone.roadmap_id == roadmap.id,
            )
            .order_by(RoadmapMilestone.phase_order, RoadmapMilestone.order_index)
        )
    )

    tier_map: dict[str, list[RoadmapMilestoneResponse]] = {name: [] for name in TIER_NAMES}
    total = len(milestones)
    done = 0

    for m in milestones:
        is_ticked = m.state == "SUPPORTED"
        if is_ticked:
            done += 1
        item = RoadmapMilestoneResponse(
            id=str(m.id),
            phase_name=m.phase_name,
            phase_order=m.phase_order,
            title=m.title,
            description=m.description,
            key_skills=m.key_skills,
            prerequisites=m.prerequisites,
            state=m.state,
            confidence=m.confidence,
            reason=m.reason,
            ticked=is_ticked,
            order_index=m.order_index,
            **(m.details or {}),
        )
        if m.phase_name in tier_map:
            tier_map[m.phase_name].append(item)
        else:
            tier_map["Foundations"].append(item)

    tiers: list[RoadmapTierResponse] = []
    for idx, name in enumerate(TIER_NAMES):
        topics = tier_map[name]
        if topics:
            tiers.append(
                RoadmapTierResponse(
                    name=name,
                    icon=TIER_ICONS[idx],
                    topics=topics,
                )
            )

    return RoadmapResponse(
        id=str(roadmap.id),
        goal=roadmap.goal,
        level=roadmap.level,
        target_date=roadmap.target_date,
        hours_per_week=roadmap.hours_per_week,
        status=roadmap.status,
        generation_mode=roadmap.generation_mode,
        fallback_reason=roadmap.fallback_reason,
        tiers=tiers,
        total=total,
        done=done,
    )


def set_skill_done(
    db: Session, *, owner_id: UUID, roadmap_id: UUID, milestone_id: UUID, skill: str, done: bool
) -> None:
    """Tick or untick one sub-topic of a milestone (the learner's own checklist)."""
    milestone = db.scalar(select(RoadmapMilestone).where(
        RoadmapMilestone.id == milestone_id, RoadmapMilestone.roadmap_id == roadmap_id,
        RoadmapMilestone.owner_id == owner_id,
    ))
    if milestone is None:
        raise ValidationError("Roadmap milestone not found")
    if skill not in (milestone.key_skills or []):
        raise ValidationError("That sub-topic is not part of this milestone")
    details = dict(milestone.details or {})
    ticked = [item for item in details.get("done_skills", []) if item != skill]
    details["done_skills"] = [*ticked, skill] if done else ticked
    milestone.details = details  # reassign: plain JSON columns don't track in-place edits
    db.commit()


def delete_roadmap(db: Session, *, owner_id: UUID, roadmap_id: UUID) -> bool:
    """Delete a roadmap and its milestones."""
    roadmap = db.scalar(
        select(Roadmap).where(
            Roadmap.id == roadmap_id,
            Roadmap.owner_id == owner_id,
        )
    )
    if roadmap is None:
        return False
    db.execute(delete(RoadmapMilestone).where(RoadmapMilestone.roadmap_id == roadmap.id))
    db.delete(roadmap)
    db.commit()
    return True
