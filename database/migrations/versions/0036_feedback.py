"""Learner feedback: problem reports and thumbs on AI answers."""

import sqlalchemy as sa
from alembic import op

revision = "0036_feedback"
down_revision = "0035_jobs_and_upload_chunks"
branch_labels = None
depends_on = None


def upgrade():
    if "feedback" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("kind", sa.String(16), nullable=False, index=True),
        sa.Column("rating", sa.String(8), nullable=True),
        sa.Column("reason", sa.String(64), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("page", sa.String(300), nullable=True),
        sa.Column("user_agent", sa.String(300), nullable=True),
        sa.Column("answer_id", sa.Uuid(), nullable=True, index=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="new", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("feedback")
