"""Closed, typed adapters over the existing orchestration handlers.

No planner or chat routing is enabled by registering capabilities here.
Legacy workflows retain their current payload and approval behaviour.
"""

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PayloadError
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.services.contexts import get_owned_context


class Params(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ContextParams(Params):
    context_id: UUID


class StudyParams(ContextParams):
    question: str = Field(min_length=1, max_length=10000)


class AssessmentParams(ContextParams):
    question_count: int = Field(default=3, ge=1, le=20, strict=True)
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class PlannerParams(ContextParams):
    days: int = Field(default=14, ge=1, le=365, strict=True)


class EvidenceParams(ContextParams):
    evidence_id: UUID


class AudioSessionParams(ContextParams):
    session_id: UUID
    # Required: a replay must not absorb later conversation turns.
    through_position: int = Field(ge=0, strict=True)


class AudioResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    artifact_id: UUID
    source_id: UUID
    status: Literal["PENDING", "PROCESSING", "READY", "FAILED"]


@dataclass(frozen=True)
class Capability:
    name: str
    params_model: type[Params]
    kind: Literal["required", "optional"]
    confirmation: Literal["none", "destructive", "replaces_existing"]
    cost: Literal["llm", "tts", "none"]
    handler: Callable
    output_model: type[BaseModel] | None = None

    @property
    def required_params(self) -> tuple[str, ...]:
        return tuple(k for k, field in self.params_model.model_fields.items() if field.is_required())

    def validate(self, payload: dict) -> Params:
        try:
            return self.params_model.model_validate(payload)
        except PayloadError as exc:
            # Do not return raw Pydantic errors containing user inputs.
            raise ValidationError("Invalid capability parameters") from exc


def _legacy_handler(name: str):
    async def call(db, *, owner_id, params):
        from app.services.orchestration import AGENTS

        payload = params.model_dump(mode="json")
        result = AGENTS[name]["handler"](
            db, owner_id=owner_id, context_id=getattr(params, "context_id", None), payload=payload
        )
        return await result if inspect.isawaitable(result) else result

    return call


async def _audio_from_session(db, *, owner_id, params):
    from app.services.audio import generate_session_audio
    from app.services.study import get_owned_session

    get_owned_session(db, owner_id=owner_id, session_id=params.session_id, context_id=params.context_id)
    artifact = await generate_session_audio(
        db, owner_id=owner_id, session_id=params.session_id, through_position=params.through_position
    )
    return {"artifact_id": artifact.id, "source_id": artifact.source_id, "status": artifact.status}


CAPABILITIES = MappingProxyType(
    {
        "study": Capability("study", StudyParams, "optional", "none", "llm", _legacy_handler("study")),
        "assessment": Capability(
            "assessment", AssessmentParams, "optional", "none", "llm", _legacy_handler("assessment")
        ),
        "learner_model": Capability(
            "learner_model", ContextParams, "required", "none", "none", _legacy_handler("learner_model")
        ),
        "notes": Capability("notes", ContextParams, "optional", "none", "llm", _legacy_handler("notes")),
        "planner": Capability("planner", PlannerParams, "optional", "none", "none", _legacy_handler("planner")),
        "progress": Capability("progress", ContextParams, "optional", "none", "none", _legacy_handler("progress")),
        "data_reset": Capability(
            "data_reset", Params, "optional", "destructive", "none", _legacy_handler("data_reset")
        ),
        "evidence": Capability(
            "evidence", EvidenceParams, "optional", "destructive", "none", _legacy_handler("evidence")
        ),
        "audio.from_session": Capability(
            "audio.from_session", AudioSessionParams, "optional", "none", "tts", _audio_from_session, AudioResult
        ),
    }
)


def get_capability(name: str) -> Capability:
    capability = CAPABILITIES.get(name)
    if capability is None:
        raise ValidationError("Unknown capability")
    return capability


async def execute_capability(db: Session, *, owner_id: UUID, name: str, payload: dict, confirmed: bool = False) -> dict:
    capability = get_capability(name)
    params = capability.validate(payload)
    if capability.confirmation != "none" and not confirmed:
        raise ValidationError("This capability requires confirmation")
    context_id = getattr(params, "context_id", None)
    if context_id is not None:
        get_owned_context(db, owner_id=owner_id, context_id=context_id)
    result = capability.handler(db, owner_id=owner_id, params=params)
    result = await result if inspect.isawaitable(result) else result
    return capability.output_model.model_validate(result).model_dump(mode="json") if capability.output_model else result
