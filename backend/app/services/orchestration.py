"""Multi-agent orchestration: registry, deterministic workflows, approvals, audit.

Agents are thin wrappers that call existing domain services; they never touch
persistence directly. Deterministic rules (ownership, scoring, approval gates)
stay outside the agents.
"""

import inspect
import logging
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PayloadValidationError
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.core.request_context import request_id_context
from app.db.models import (
    AgentTask,
    ApprovalRequest,
    AuditLog,
    Workflow,
)
from app.services.adaptation import run_learner_loop
from app.services.assessment import create_assessment
from app.services.contexts import get_owned_context
from app.services.evidence import invalidate_evidence
from app.services.notes import generate_note
from app.services.planner import upcoming_deadlines
from app.services.progress import consistency
from app.services.study import answer_question

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2


def _now() -> datetime:
    return datetime.now(UTC)


async def _agent_study(db, *, owner_id: UUID, context_id: UUID | None, payload: dict) -> dict:
    result = await answer_question(
        db,
        owner_id=owner_id,
        context_id=context_id,
        question=payload.get("question", "Explain the current material"),
    )
    return {"content": result.content[:500], "fallback_used": result.fallback_used}


async def _agent_assessment(db, *, owner_id: UUID, context_id: UUID | None, payload: dict) -> dict:
    assessment = await create_assessment(
        db,
        owner_id=owner_id,
        context_id=context_id,
        format_name="mcq",
        question_count=payload.get("question_count", 3),
        difficulty=payload.get("difficulty", "medium"),
        mode="BASELINE",
        concept_ids=[],
    )
    return {"assessment_id": str(assessment.id), "mode": assessment.mode}


def _agent_learner_model(db, *, owner_id: UUID, context_id: UUID | None, payload: dict) -> dict:
    states, decisions = run_learner_loop(db, owner_id=owner_id, context_id=context_id)
    return {"states": len(states), "decisions": len(decisions)}


async def _agent_notes(db, *, owner_id: UUID, context_id: UUID | None, payload: dict) -> dict:
    note = await generate_note(db, owner_id=owner_id, context_id=context_id)
    return {"note_id": str(note.id), "title": note.title}


def _agent_planner(db, *, owner_id: UUID, context_id: UUID | None, payload: dict) -> dict:
    deadlines = upcoming_deadlines(db, owner_id=owner_id, days=payload.get("days", 14))
    return {
        "upcoming": [
            {"id": str(item.id), "title": item.title}
            for item in deadlines[:3]
        ]
    }


def _agent_progress(db, *, owner_id: UUID, context_id: UUID | None, payload: dict) -> dict:
    stats = consistency(db, owner_id=owner_id)
    return {
        "current_streak": stats["current_streak"],
        "active_this_month": stats["active_this_month"],
    }


def _agent_data_reset(db, *, owner_id: UUID, context_id: UUID | None, payload: dict) -> dict:
    from app.services.account import reset_learner_data

    reset_learner_data(db, owner_id=owner_id)
    return {"deleted": True}


def _agent_evidence(db, *, owner_id: UUID, context_id: UUID | None, payload: dict) -> dict:
    evidence_id = UUID(payload["evidence_id"])
    effective_context_id = context_id
    if effective_context_id is None and payload.get("context_id"):
        effective_context_id = UUID(str(payload["context_id"]))
    if effective_context_id is None:
        raise ValidationError("context_id is required for evidence invalidation")
    invalidate_evidence(db, owner_id=owner_id, evidence_id=evidence_id, context_id=effective_context_id)
    run_learner_loop(db, owner_id=owner_id, context_id=effective_context_id)
    return {"evidence_id": str(evidence_id), "invalidated": True}


def _agent(handler, *, capabilities: list[str], needs_approval: bool = False) -> dict:
    return {
        "capabilities": capabilities,
        "needs_approval": needs_approval,
        "handler": handler,
    }


AGENTS = {
    "study": _agent(_agent_study, capabilities=["answer"]),
    "assessment": _agent(_agent_assessment, capabilities=["create"]),
    "learner_model": _agent(_agent_learner_model, capabilities=["recompute"]),
    "notes": _agent(_agent_notes, capabilities=["generate"]),
    "planner": _agent(_agent_planner, capabilities=["upcoming"]),
    "progress": _agent(_agent_progress, capabilities=["consistency"]),
    "data_reset": _agent(_agent_data_reset, capabilities=["delete_all"], needs_approval=True),
    "evidence": _agent(_agent_evidence, capabilities=["invalidate"], needs_approval=True),
}

WORKFLOWS = {
    "learning_cycle": {
        "steps": [{"agent": "study"}, {"agent": "assessment"}, {"agent": "learner_model"}]
    },
    "generate_notes": {"steps": [{"agent": "notes"}]},
    "exam_prep": {"steps": [{"agent": "planner"}, {"agent": "notes"}, {"agent": "progress"}]},
    "data_reset": {"steps": [{"agent": "data_reset"}]},
    "evidence_invalidate": {"steps": [{"agent": "evidence"}]},
}


def record_audit(db: Session, *, owner_id: UUID, agent: str, action: str, detail: dict) -> None:
    db.add(
        AuditLog(
            owner_id=owner_id,
            agent=agent,
            action=action,
            detail=detail,
            request_id=request_id_context.get(),
        )
    )
    db.commit()


async def _run_step(
    db: Session, *, owner_id: UUID, workflow: Workflow, task: AgentTask,
    agent: dict, context_id: UUID | None, payload: dict,
) -> bool:
    output = None
    handler_finished = False
    for attempt in range(1, MAX_ATTEMPTS + 1):
        committed = False
        def mark_commit(session):
            nonlocal committed
            committed = True
        try:
            task.attempt = attempt
            task.status = "RUNNING"
            db.add(task)
            db.commit()
            if not handler_finished:
                # Observe domain commits, not our own task/audit metadata writes.
                event.listen(db, "after_commit", mark_commit)
                try:
                    result = agent["handler"](
                        db, owner_id=owner_id, context_id=context_id, payload=payload
                    )
                    output = await result if inspect.isawaitable(result) else result
                    handler_finished = True
                finally:
                    event.remove(db, "after_commit", mark_commit)
            task.status = "SUCCEEDED"
            task.error_detail = None
            task.output_refs = {"output": output}
            db.add(task)
            db.add(AuditLog(
                owner_id=owner_id, agent=task.agent, action="succeeded",
                detail={"workflow_id": str(workflow.id), "output": output},
                request_id=request_id_context.get(),
            ))
            db.commit()
            return True
        except Exception as exc:
            # Failed SQL sessions must roll back before recovery writes.
            db.rollback()
            message = (
                "Step failed after committing changes. Review the result before retrying."
                if committed and not handler_finished
                else "Workflow step failed. Please retry or contact support."
            )
            logger.warning("workflow step failed agent=%s error_type=%s", task.agent, type(exc).__name__)
            task.error_detail = message
            db.add(task)
            db.add(AuditLog(
                owner_id=owner_id, agent=task.agent, action="failed",
                detail={"workflow_id": str(workflow.id), "error": message},
                request_id=request_id_context.get(),
            ))
            db.commit()
            if committed and not handler_finished:
                # An unknown post-commit outcome is not safe to replay. Once a
                # handler returns, however, retries persist its cached output
                # without executing its domain work a second time.
                break
    task.status = "FAILED"
    db.add(task)
    db.commit()
    return False


def _notify_terminal(db: Session, *, owner_id: UUID, workflow: Workflow) -> None:
    from app.services.notifications import dispatch_notification

    try:
        dispatch_notification(
            db,
            owner_id=owner_id,
            ntype="workflow",
            title=f"Workflow '{workflow.name}' {workflow.status.lower()}",
            body=workflow.error_detail
            or f"The {workflow.name} workflow finished with status {workflow.status}.",
        )
    except Exception:
        logger.exception("workflow completion notification failed")


async def _advance(
    db: Session, *, owner_id: UUID, workflow: Workflow, payload: dict
) -> ApprovalRequest | None:
    steps = WORKFLOWS[workflow.name]["steps"]
    context_id = UUID(payload["context_id"]) if payload.get("context_id") else None
    for index in range(workflow.current_step, len(steps)):
        step_def = steps[index]
        agent = AGENTS[step_def["agent"]]
        task = AgentTask(
            owner_id=owner_id,
            workflow_id=workflow.id,
            agent=step_def["agent"],
            status="PENDING",
        )
        db.add(task)
        db.flush()
        workflow.current_step = index
        if agent["needs_approval"]:
            task.status = "WAITING_APPROVAL"
            db.add(task)
            approval = ApprovalRequest(
                owner_id=owner_id,
                workflow_id=workflow.id,
                action=step_def["agent"],
                detail=f"Approve '{step_def['agent']}' step of workflow '{workflow.name}'",
            )
            db.add(approval)
            workflow.status = "WAITING_APPROVAL"
            db.add(workflow)
            db.commit()
            return approval
        ok = await _run_step(
            db,
            owner_id=owner_id,
            workflow=workflow,
            task=task,
            agent=agent,
            context_id=context_id,
            payload=payload,
        )
        if not ok:
            workflow.status = "FAILED"
            workflow.error_detail = task.error_detail
            db.add(workflow)
            db.commit()
            _notify_terminal(db, owner_id=owner_id, workflow=workflow)
            return None
    workflow.status = "COMPLETED"
    workflow.current_step = len(steps)
    db.add(workflow)
    db.commit()
    _notify_terminal(db, owner_id=owner_id, workflow=workflow)
    return None


class WorkflowPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    context_id: UUID | None = None
    evidence_id: UUID | None = None
    question: str = Field(default="Explain the current material", min_length=1, max_length=10000)
    question_count: int = Field(default=3, ge=1, le=20)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    days: int = Field(default=14, ge=1, le=365)


def _validate_payload(db: Session, *, owner_id: UUID, name: str, payload: dict) -> dict:
    try:
        validated = WorkflowPayload.model_validate(payload)
    except PayloadValidationError as exc:
        raise ValidationError("Invalid workflow parameters") from exc
    if name != "data_reset" and validated.context_id is None:
        raise ValidationError("context_id is required for this workflow")
    if name == "evidence_invalidate" and validated.evidence_id is None:
        raise ValidationError("evidence_id is required for this workflow")
    if validated.context_id is not None:
        get_owned_context(db, owner_id=owner_id, context_id=validated.context_id)
    return validated.model_dump(mode="json", exclude_none=True)


async def run_workflow(
    db: Session, *, owner_id: UUID, name: str, payload: dict,
    idempotency_claim: tuple[str, str, UUID] | None = None,
) -> tuple[Workflow, ApprovalRequest | None]:
    if name not in WORKFLOWS:
        raise ValidationError(f"Unknown workflow: {name}")
    payload = _validate_payload(db, owner_id=owner_id, name=name, payload=payload or {})
    workflow = Workflow(owner_id=owner_id, name=name, status="RUNNING", payload=payload or {})
    db.add(workflow)
    if idempotency_claim is not None:
        from app.services.idempotency import bind_workflow

        db.flush()
        scope, key, claim_id = idempotency_claim
        bind_workflow(db, owner_id=owner_id, scope=scope, key=key, claim_id=claim_id, workflow_id=workflow.id)
    db.commit()
    db.refresh(workflow)
    approval = await _advance(db, owner_id=owner_id, workflow=workflow, payload=workflow.payload)
    db.refresh(workflow)
    return workflow, approval


async def decide_approval(
    db: Session, *, owner_id: UUID, approval_id: UUID, approved: bool
) -> tuple[Workflow, ApprovalRequest | None]:
    approval = db.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.id == approval_id, ApprovalRequest.owner_id == owner_id
        )
    )
    if approval is None:
        raise ValidationError("Approval request not found")
    if approval.status != "PENDING":
        raise ValidationError("Approval already decided")
    workflow = db.scalar(
        select(Workflow).where(
            Workflow.id == approval.workflow_id, Workflow.owner_id == owner_id
        )
    )
    if workflow is None:
        raise ValidationError("Workflow not found")
    if approved:
        workflow.payload = _validate_payload(db, owner_id=owner_id, name=workflow.name, payload=workflow.payload)
    approval.status = "APPROVED" if approved else "REJECTED"
    approval.decided_at = _now()
    db.add(approval)
    if not approved:
        workflow.status = "REJECTED"
        db.add(workflow)
        db.commit()
        record_audit(
            db,
            owner_id=owner_id,
            agent=approval.action,
            action="rejected",
            detail={"workflow_id": str(workflow.id), "approval_id": str(approval.id)},
        )
        _notify_terminal(db, owner_id=owner_id, workflow=workflow)
        return workflow, None

    # Validate the waiting task BEFORE consuming the approval, so a mismatch
    # leaves the approval pending and the workflow retryable instead of
    # committing an irreversible state and stranding the workflow RUNNING.
    task = db.scalar(
        select(AgentTask).where(
            AgentTask.workflow_id == workflow.id,
            AgentTask.agent == approval.action,
            AgentTask.status == "WAITING_APPROVAL",
        )
    )
    if task is None:
        raise ValidationError("Waiting task not found")
    workflow.status = "RUNNING"
    db.add(workflow)
    db.commit()
    record_audit(
        db,
        owner_id=owner_id,
        agent=approval.action,
        action="approved",
        detail={"workflow_id": str(workflow.id), "approval_id": str(approval.id)},
    )
    agent = AGENTS[approval.action]
    context_id = (
        UUID(workflow.payload["context_id"]) if workflow.payload.get("context_id") else None
    )
    ok = await _run_step(
        db,
        owner_id=owner_id,
        workflow=workflow,
        task=task,
        agent=agent,
        context_id=context_id,
        payload=workflow.payload,
    )
    if not ok:
        workflow.status = "FAILED"
        db.add(workflow)
        workflow.error_detail = task.error_detail
        db.add(workflow)
        db.commit()
        _notify_terminal(db, owner_id=owner_id, workflow=workflow)
        return workflow, None
    workflow.current_step += 1
    db.add(workflow)
    db.commit()
    approval_after = await _advance(
        db, owner_id=owner_id, workflow=workflow, payload=workflow.payload
    )
    db.refresh(workflow)
    return workflow, approval_after


def list_workflows(db: Session, *, owner_id: UUID) -> list[Workflow]:
    return list(
        db.scalars(
            select(Workflow)
            .where(Workflow.owner_id == owner_id)
            .order_by(Workflow.created_at.desc())
            .limit(20)
        )
    )


def get_workflow(db: Session, *, owner_id: UUID, workflow_id: UUID) -> Workflow:
    workflow = db.scalar(
        select(Workflow).where(
            Workflow.id == workflow_id, Workflow.owner_id == owner_id
        )
    )
    if workflow is None:
        raise ValidationError("Workflow not found")
    return workflow


def pending_approvals(db: Session, *, owner_id: UUID) -> list[ApprovalRequest]:
    return list(
        db.scalars(
            select(ApprovalRequest)
            .where(ApprovalRequest.owner_id == owner_id, ApprovalRequest.status == "PENDING")
            .order_by(ApprovalRequest.created_at.desc())
        )
    )


def list_audit(db: Session, *, owner_id: UUID) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.owner_id == owner_id)
            .order_by(AuditLog.created_at.desc())
            .limit(50)
        )
    )
