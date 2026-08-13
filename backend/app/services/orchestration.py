"""Multi-agent orchestration: registry, deterministic workflows, approvals, audit.

Agents are thin wrappers that call existing domain services; they never touch
persistence directly. Deterministic rules (ownership, scoring, approval gates)
stay outside the agents.
"""

import inspect
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
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
from app.services.evidence import invalidate_evidence
from app.services.notes import generate_note
from app.services.planner import upcoming_deadlines
from app.services.progress import consistency
from app.services.study import answer_question

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
    invalidate_evidence(db, owner_id=owner_id, evidence_id=evidence_id)
    if context_id is not None:
        run_learner_loop(db, owner_id=owner_id, context_id=context_id)
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
    db: Session,
    *,
    owner_id: UUID,
    workflow: Workflow,
    task: AgentTask,
    agent: dict,
    context_id: UUID | None,
    payload: dict,
) -> bool:
    handler = agent["handler"]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        task.attempt = attempt
        task.status = "RUNNING"
        db.add(task)
        db.commit()
        try:
            result = handler(db, owner_id=owner_id, context_id=context_id, payload=payload)
            output = await result if inspect.isawaitable(result) else result
            task.status = "SUCCEEDED"
            task.output_refs = {"output": output}
            db.add(task)
            db.commit()
            record_audit(
                db,
                owner_id=owner_id,
                agent=task.agent,
                action="succeeded",
                detail={"workflow_id": str(workflow.id), "output": output},
            )
            return True
        except Exception as exc:  # noqa: BLE001 - workflow steps must be resilient
            task.error_detail = str(exc)[:500]
            db.add(task)
            db.commit()
            record_audit(
                db,
                owner_id=owner_id,
                agent=task.agent,
                action="failed",
                detail={"workflow_id": str(workflow.id), "error": str(exc)[:200]},
            )
    task.status = "FAILED"
    db.add(task)
    db.commit()
    return False


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
            return None
    workflow.status = "COMPLETED"
    workflow.current_step = len(steps)
    db.add(workflow)
    db.commit()
    return None


async def run_workflow(
    db: Session, *, owner_id: UUID, name: str, payload: dict
) -> tuple[Workflow, ApprovalRequest | None]:
    if name not in WORKFLOWS:
        raise ValidationError(f"Unknown workflow: {name}")
    workflow = Workflow(owner_id=owner_id, name=name, status="RUNNING", payload=payload or {})
    db.add(workflow)
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
        return workflow, None

    workflow.status = "RUNNING"
    db.add(workflow)
    db.commit()
    task = db.scalar(
        select(AgentTask).where(
            AgentTask.workflow_id == workflow.id,
            AgentTask.agent == approval.action,
            AgentTask.status == "WAITING_APPROVAL",
        )
    )
    if task is None:
        raise ValidationError("Waiting task not found")
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
