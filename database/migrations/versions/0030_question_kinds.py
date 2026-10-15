"""Question kinds (true/false, short answer) and per-question explanations."""

import sqlalchemy as sa
from alembic import op

revision = "0030_question_kinds"
down_revision = "0029_chat_attachments"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("assessment_questions")}
    with op.batch_alter_table("assessment_questions") as batch:
        if "kind" not in columns:
            batch.add_column(sa.Column("kind", sa.String(16), nullable=False, server_default="mcq"))
        if "explanation" not in columns:
            batch.add_column(sa.Column("explanation", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("assessment_questions") as batch:
        batch.drop_column("explanation")
        batch.drop_column("kind")
