"""Add learner email verification (verified_at column)."""

import sqlalchemy as sa
from alembic import op

revision = "0014_email_verification"
down_revision = "0013_ai_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("learners")}
    if "verified_at" not in columns:
        op.add_column(
            "learners", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    op.drop_column("learners", "verified_at")
