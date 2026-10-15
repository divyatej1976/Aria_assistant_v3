"""LangGraph is the sole runtime for new chat actions.

Only opaque identifiers and enum status values cross node boundaries.
Conversation text and learner snapshots never enter graph state/config.
"""

from typing import TypedDict
from uuid import UUID

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy import update

from app.core.config import get_settings
from app.core.errors import ValidationError
from app.db.models import BrainAction
from app.services.brain.actions import audit, owned_action
from app.services.brain.capabilities import execute_capability


class ActionState(TypedDict, total=False):
    action_id: str
    owner_id: str
    artifact_id: str
    outcome: str


async def execute_graph(db, *, owner_id, action_id, claim_id):
    if db.get_bind().dialect.name != "sqlite":
        raise ValidationError("PostgreSQL graph checkpoint storage is not enabled yet")

    async def validate(state):
        action = owned_action(db, owner_id=owner_id, action_id=action_id)
        if action.capability != "audio.from_session" or action.claim_id != claim_id:
            raise ValidationError("Invalid or superseded action")
        return {"action_id": str(action_id), "owner_id": str(owner_id)}

    async def execute(state):
        action = owned_action(db, owner_id=owner_id, action_id=action_id)
        if action.claim_id != claim_id:
            raise ValidationError("Action claim was replaced")
        try:
            result = await execute_capability(
                db,
                owner_id=owner_id,
                name="audio.from_session",
                payload={
                    "context_id": str(action.context_id),
                    "session_id": str(action.session_id),
                    "source_id": str(action.source_id),
                    "through_position": action.through_position,
                },
            )
        except Exception:
            # Checkpointers also persist node errors. Never checkpoint a raw
            # provider/database exception which could contain source text.
            raise ValidationError("Audio execution failed") from None
        if result["status"] == "FAILED":
            raise ValidationError("Audio generation failed")
        return {"artifact_id": result["artifact_id"], "outcome": "done" if result["status"] == "READY" else "running"}

    async def report(state):
        changed = db.execute(
            update(BrainAction)
            .where(BrainAction.id == action_id, BrainAction.owner_id == owner_id, BrainAction.claim_id == claim_id)
            .values(
                status=state["outcome"],
                artifact_id=UUID(state["artifact_id"]),
                lease_until=None,
                claim_id=None,
                error_code=None,
            )
        ).rowcount
        if not changed:
            db.rollback()
            raise ValidationError("Action claim was replaced")
        audit(db, owned_action(db, owner_id=owner_id, action_id=action_id), state["outcome"])
        db.commit()
        return {}

    builder = StateGraph(ActionState)
    builder.add_node("validate", validate)
    builder.add_node("execute", execute)
    builder.add_node("report", report)
    builder.add_edge(START, "validate")
    builder.add_edge("validate", "execute")
    builder.add_edge("execute", "report")
    builder.add_edge("report", END)
    async with AsyncSqliteSaver.from_conn_string(get_settings().aria_brain_checkpoint_path) as saver:
        graph = builder.compile(checkpointer=saver, interrupt_before=["execute"], name="aria_audio_action")
        config = {"configurable": {"thread_id": f"{owner_id}:{action_id}"}}
        saved = await graph.aget_state(config)
        if not saved.next:
            await graph.ainvoke({"action_id": str(action_id), "owner_id": str(owner_id)}, config)
        # Resume begins at the interrupted execute node. The capability uses
        # its immutable source and existing audio lease/reuse protections.
        await graph.ainvoke(None, config)
