"""Persist generated/fallback provenance on chat messages."""

import sqlalchemy as sa
from alembic import op

revision = "0020_chat_fallback"
down_revision = "0019_roadmaps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("conversation_messages")}
    if "fallback_used" not in columns:
        op.add_column("conversation_messages", sa.Column("fallback_used", sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("conversation_messages") as batch:
        batch.drop_column("fallback_used")
