"""Add shared rate-limit buckets (multi-replica safe)."""

import sqlalchemy as sa
from alembic import op

revision = "0016_rate_limit_buckets"
down_revision = "0015_learner_llm_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("rate_limit_buckets"):
        op.create_table(
            "rate_limit_buckets",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("key", sa.String(length=255), nullable=False),
            sa.Column("window_started_at", sa.DateTime(), nullable=False),
            sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_rate_limit_buckets_key", "rate_limit_buckets", ["key"], unique=True)


def downgrade() -> None:
    op.drop_table("rate_limit_buckets")
