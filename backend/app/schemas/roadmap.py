import re
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, PrivateAttr, StringConstraints, field_validator, model_validator

RoadmapGoal = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
RoadmapTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
RoadmapSkill = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class GeneratedMilestone(BaseModel):
    title: RoadmapTitle = Field(description="Title of the topic/milestone")
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)]
    key_skills: list[RoadmapSkill] = Field(
        default_factory=list, max_length=20,
        description="Key skills and concepts needed to master this milestone",
    )
    prerequisites: list[RoadmapTitle] = Field(
        default_factory=list, max_length=20,
        description="Titles of earlier milestones that must be completed first",
    )


class GeneratedPhase(BaseModel):
    phase_name: Literal["Foundations", "Core Concepts", "Advanced Topics", "Mastery Track"] = Field(
        description="Name of the phase (Foundations, Core Concepts, Advanced Topics, Mastery Track)"
    )
    milestones: list[GeneratedMilestone] = Field(
        min_length=1, max_length=12, description="Milestones belonging to this phase"
    )


class GeneratedRoadmapTree(BaseModel):
    # Application provenance must never be supplied by the model itself.
    _generation_mode: str | None = PrivateAttr(default=None)
    _fallback_reason: str | None = PrivateAttr(default=None)
    goal: RoadmapGoal
    level: Literal["Beginner", "Intermediate", "Advanced"]
    phases: list[GeneratedPhase] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_structure(self):
        phase_order = ["Foundations", "Core Concepts", "Advanced Topics", "Mastery Track"]
        names = [phase.phase_name for phase in self.phases]
        if len(set(names)) != len(names) or names != sorted(names, key=phase_order.index):
            raise ValueError("Roadmap phases must be distinct and ordered")
        seen = set()
        for phase in self.phases:
            for milestone in phase.milestones:
                title = " ".join(re.findall(r"\w+", milestone.title.casefold()))
                if not title or title in seen:
                    raise ValueError("Milestone titles must be meaningful and unique")
                requirements = [" ".join(re.findall(r"\w+", value.casefold())) for value in milestone.prerequisites]
                if len(set(requirements)) != len(requirements) or any(value not in seen for value in requirements):
                    raise ValueError("Prerequisites must name distinct earlier milestones")
                skills = [" ".join(re.findall(r"\w+", value.casefold())) for value in milestone.key_skills]
                if any(not skill for skill in skills) or len(set(skills)) != len(skills):
                    raise ValueError("Skills must be meaningful and distinct within a milestone")
                seen.add(title)
        return self


class RoadmapCreateRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=255)
    level: Literal["Beginner", "Intermediate", "Advanced"] = "Beginner"
    target_date: str | None = Field(default=None, max_length=10)
    hours_per_week: int | None = Field(default=None, ge=1, le=60)
    context_id: UUID | None = None

    @field_validator("goal")
    @classmethod
    def clean_goal(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Learning goal is required")
        return cleaned

    @field_validator("target_date")
    @classmethod
    def validate_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Target date must be a valid YYYY-MM-DD date") from exc
        if parsed.isoformat() != value:
            raise ValueError("Target date must use YYYY-MM-DD")
        return value


class RoadmapMilestoneResponse(BaseModel):
    id: str
    phase_name: str
    phase_order: int
    title: str
    description: str | None = None
    key_skills: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    state: str
    confidence: int
    reason: str | None = None
    ticked: bool
    order_index: int


class RoadmapTierResponse(BaseModel):
    name: str
    icon: str
    topics: list[RoadmapMilestoneResponse]


class RoadmapResponse(BaseModel):
    id: str
    goal: str
    level: str
    target_date: str | None = None
    hours_per_week: int | None = None
    status: str
    generation_mode: Literal["ai", "starter"] | None = None
    fallback_reason: Literal["provider_unavailable", "provider_failed", "invalid_output"] | None = None
    tiers: list[RoadmapTierResponse]
    total: int
    done: int


class RoadmapSummaryResponse(BaseModel):
    id: str
    goal: str
    level: str
    target_date: str | None = None
    hours_per_week: int | None = None
    status: str
    generation_mode: Literal["ai", "starter"] | None = None
    fallback_reason: Literal["provider_unavailable", "provider_failed", "invalid_output"] | None = None
    created_at: str
    total: int
    done: int
