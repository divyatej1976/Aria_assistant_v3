"""Add planner entities: deadlines, planned tasks, and notifications."""

import sqlalchemy as sa
from alembic import op

revision = "0006_planner"
down_revision = "0005_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("deadlines"):
        op.create_table(
            "deadlines",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("context_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=False, index=True),
            sa.Column("syllabus_resource_id", sa.Uuid(), nullable=True, index=True),
            sa.Column("reminder_days_before", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("reminder_sent_days_before", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
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
            sa.ForeignKeyConstraint(["syllabus_resource_id"], ["resources.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not inspector.has_table("planned_tasks"):
        op.create_table(
            "planned_tasks",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("context_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("deadline_id", sa.Uuid(), nullable=True, index=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            sa.ForeignKeyConstraint(["deadline_id"], ["deadlines.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    if not inspector.has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("ntype", sa.String(length=64), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
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


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("planned_tasks")
    op.drop_table("deadlines")
