"""Weekly study time on roadmaps, used to pace the plan and "This week"."""

import sqlalchemy as sa
from alembic import op

revision = "0031_roadmap_hours"
down_revision = "0030_question_kinds"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("roadmaps")}
    if "hours_per_week" not in columns:
        with op.batch_alter_table("roadmaps") as batch:
            batch.add_column(sa.Column("hours_per_week", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("roadmaps") as batch:
        batch.drop_column("hours_per_week")
