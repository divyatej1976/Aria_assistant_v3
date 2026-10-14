"""Add per-learner BYO LLM keys and per-learner AI usage (Step 4)."""

import sqlalchemy as sa
from alembic import op

revision = "0015_learner_llm_keys"
down_revision = "0014_email_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("learner_llm_keys"):
        op.create_table(
            "learner_llm_keys",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False, server_default="groq"),
            sa.Column("encrypted_key", sa.Text(), nullable=False),
            sa.Column("key_hint", sa.String(length=16), nullable=False),
            sa.Column("model", sa.String(length=128), nullable=True),
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
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("owner_id", name="uq_learner_llm_key_owner"),
        )
        op.create_index("ix_learner_llm_keys_owner_id", "learner_llm_keys", ["owner_id"])
    if not inspector.has_table("learner_ai_usage"):
        op.create_table(
            "learner_ai_usage",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False),
            sa.Column("period", sa.String(length=7), nullable=False),
            sa.Column("spend_usd", sa.Float(), nullable=False, server_default="0"),
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
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "owner_id", "period", name="uq_learner_ai_usage_owner_period"
            ),
        )
        op.create_index("ix_learner_ai_usage_owner_id", "learner_ai_usage", ["owner_id"])


def downgrade() -> None:
    op.drop_table("learner_ai_usage")
    op.drop_table("learner_llm_keys")
