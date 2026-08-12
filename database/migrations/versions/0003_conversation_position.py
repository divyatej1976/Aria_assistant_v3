"""Add a monotonic position to conversation messages.

created_at has second granularity, so messages sent in the same second had
unstable ordering. position is assigned at insert time and used for ordering
conversation history deterministically.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_conversation_position"
down_revision = "0002_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("conversation_messages")}
    if "position" not in columns:
        op.add_column(
            "conversation_messages",
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    op.drop_column("conversation_messages", "position")
