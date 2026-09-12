"""Widen assessment answer columns to unbounded text.

PostgreSQL enforces varchar(32) while SQLite does not: option text generated
from real study material (e.g. "Loops repeat a block while a condition
holds", 46 chars) crashed assessment submission with StringDataRightTruncation.
correct_option is widened too — it stores a letter today, but the answer
contract accepts option text and must never depend on column width.

Fresh databases build both tables from current metadata (0001 create_all),
so this migration only patches legacy Postgres databases; guarded to PG.
"""

import sqlalchemy as sa
from alembic import op

revision = "0018_assessment_answer_text"
down_revision = "0017_owner_scoped_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    # varchar -> text is a metadata-only change in PostgreSQL.
    op.alter_column(
        "assessment_questions",
        "correct_option",
        existing_type=sa.String(length=32),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "attempt_answers",
        "selected_option",
        existing_type=sa.String(length=32),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.alter_column(
        "attempt_answers",
        "selected_option",
        existing_type=sa.Text(),
        type_=sa.String(length=32),
        existing_nullable=True,
    )
    op.alter_column(
        "assessment_questions",
        "correct_option",
        existing_type=sa.Text(),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
