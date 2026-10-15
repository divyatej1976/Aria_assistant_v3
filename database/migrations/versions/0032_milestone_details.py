"""Milestone outcome/effort/activity/check, and the roadmap focus reused when refining."""

import sqlalchemy as sa
from alembic import op

revision = "0032_milestone_details"
down_revision = "0031_roadmap_hours"
branch_labels = None
depends_on = None


def upgrade():
    inspect = sa.inspect(op.get_bind())
    if "focus" not in {c["name"] for c in inspect.get_columns("roadmaps")}:
        with op.batch_alter_table("roadmaps") as batch:
            batch.add_column(sa.Column("focus", sa.String(16), nullable=True))
    if "details" not in {c["name"] for c in inspect.get_columns("roadmap_milestones")}:
        with op.batch_alter_table("roadmap_milestones") as batch:
            batch.add_column(sa.Column("details", sa.JSON(), nullable=False, server_default="{}"))


def downgrade():
    with op.batch_alter_table("roadmap_milestones") as batch:
        batch.drop_column("details")
    with op.batch_alter_table("roadmaps") as batch:
        batch.drop_column("focus")
