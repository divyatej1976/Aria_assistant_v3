"""Add a unique (study_session_id, position) constraint to conversation messages.

The baseline migration creates tables from the ORM models, so fresh databases
already carry this constraint (added to the model). This migration only acts on
databases created before the constraint existed, and is a no-op otherwise.
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_conversation_position"
down_revision = "0011_vector"
branch_labels = None
depends_on = None

CONSTRAINT = "uq_conversation_message_position"


def _has_constraint(bind) -> bool:
    inspector = sa.inspect(bind)
    try:
        names = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("conversation_messages")
        }
    except Exception:
        return True
    return CONSTRAINT in names


def upgrade() -> None:
    bind = op.get_bind()
    if _has_constraint(bind):
        return
    if bind.dialect.name == "postgresql":
        op.create_unique_constraint(
            CONSTRAINT, "conversation_messages", ["study_session_id", "position"]
        )
    else:
        with op.batch_alter_table("conversation_messages") as batch_op:
            batch_op.create_unique_constraint(
                CONSTRAINT, ["study_session_id", "position"]
            )


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_constraint(bind):
        return
    if bind.dialect.name == "postgresql":
        op.drop_constraint(CONSTRAINT, "conversation_messages", type_="unique")
    else:
        with op.batch_alter_table("conversation_messages") as batch_op:
            batch_op.drop_constraint(CONSTRAINT, type_="unique")
