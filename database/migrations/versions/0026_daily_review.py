"""One durable daily review per learner and subject."""

import sqlalchemy as sa
from alembic import op

revision = "0026_daily_review"
down_revision = "0025_workflow_checkpoint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("assessments")}
    constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("assessments")}
    # The metadata-driven foundation already includes the current model on a
    # fresh install. Older databases still need both additions.
    with op.batch_alter_table("assessments") as batch:
        if "daily_review_date" not in columns:
            batch.add_column(sa.Column("daily_review_date", sa.String(10), nullable=True))
        if "uq_assessment_daily_review" not in constraints:
            batch.create_unique_constraint(
                "uq_assessment_daily_review", ["owner_id", "context_id", "daily_review_date"]
            )


def downgrade() -> None:
    with op.batch_alter_table("assessments") as batch:
        batch.drop_constraint("uq_assessment_daily_review", type_="unique")
        batch.drop_column("daily_review_date")
