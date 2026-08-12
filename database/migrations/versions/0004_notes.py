"""Add learner notes and their spaced-revision items."""

import sqlalchemy as sa
from alembic import op

revision = "0004_notes"
down_revision = "0003_conversation_position"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("notes"):
        op.create_table(
            "notes",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("context_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("resource_id", sa.Uuid(), nullable=True, index=True),
            sa.Column("concept_id", sa.Uuid(), nullable=True, index=True),
            sa.Column("study_session_id", sa.Uuid(), nullable=True, index=True),
            sa.Column("source_refs", sa.JSON(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["owner_id"], ["learners.id"]),
            sa.ForeignKeyConstraint(["context_id"], ["learning_contexts.id"]),
            sa.ForeignKeyConstraint(["resource_id"], ["resources.id"]),
            sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"]),
            sa.ForeignKeyConstraint(["study_session_id"], ["study_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not inspector.has_table("revision_items"):
        op.create_table(
            "revision_items",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("note_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("state", sa.String(length=32), nullable=False, server_default="NEW"),
            sa.Column("interval_days", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_outcome", sa.String(length=32), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["owner_id"], ["learners.id"]),
            sa.ForeignKeyConstraint(["note_id"], ["notes.id"]),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("revision_items")
    op.drop_table("notes")
