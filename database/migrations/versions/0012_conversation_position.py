"""Add a unique (study_session_id, position) constraint to conversation messages."""

import sqlalchemy as sa
from alembic import op

revision = "0012_conversation_position"
down_revision = "0011_vector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_conversation_message_position",
        "conversation_messages",
        ["study_session_id", "position"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_conversation_message_position", "conversation_messages", type_="unique"
    )
