"""Add learning activity records and earned badges for progress tracking."""

import sqlalchemy as sa
from alembic import op

revision = "0005_progress"
down_revision = "0004_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("learning_activities"):
        op.create_table(
            "learning_activities",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("activity_type", sa.String(length=64), nullable=False, index=True),
            sa.Column("occurred_on", sa.Date(), nullable=False, index=True),
            sa.Column("source_id", sa.Uuid(), nullable=True),
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
            sa.PrimaryKeyConstraint("id"),
        )
    if not inspector.has_table("learner_badges"):
        op.create_table(
            "learner_badges",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("label", sa.String(length=120), nullable=False),
            sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
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
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("owner_id", "code", name="uq_learner_badge_code"),
        )


def downgrade() -> None:
    op.drop_table("learner_badges")
    op.drop_table("learning_activities")
