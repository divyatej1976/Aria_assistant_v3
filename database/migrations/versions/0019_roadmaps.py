"""Add roadmaps and roadmap_milestones tables.

This creates the isolated roadmap and milestone tables for goal-driven curriculum trees.
"""

import sqlalchemy as sa
from alembic import op

revision = "0019_roadmaps"
down_revision = "0018_assessment_answer_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("roadmaps"):
        op.create_table(
            "roadmaps",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("context_id", sa.Uuid(), nullable=True, index=True),
            sa.Column("goal", sa.String(length=255), nullable=False),
            sa.Column("level", sa.String(length=64), server_default="Beginner", nullable=False),
            sa.Column("target_date", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
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
            sa.ForeignKeyConstraint(["context_id"], ["learning_contexts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not inspector.has_table("roadmap_milestones"):
        op.create_table(
            "roadmap_milestones",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("roadmap_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("phase_name", sa.String(length=120), nullable=False),
            sa.Column("phase_order", sa.Integer(), server_default="0", nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("key_skills", sa.JSON(), nullable=False),
            sa.Column("prerequisites", sa.JSON(), nullable=False),
            sa.Column("state", sa.String(length=32), server_default="NOT_STARTED", nullable=False),
            sa.Column("confidence", sa.Integer(), server_default="0", nullable=False),
            sa.Column("reason", sa.String(length=255), nullable=True),
            sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
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
            sa.ForeignKeyConstraint(["roadmap_id"], ["roadmaps.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("roadmap_milestones"):
        op.drop_table("roadmap_milestones")
    if inspector.has_table("roadmaps"):
        op.drop_table("roadmaps")
