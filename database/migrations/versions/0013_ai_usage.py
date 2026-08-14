"""Add a persistent monthly AI usage table for budget accounting."""

import sqlalchemy as sa
from alembic import op

revision = "0013_ai_usage"
down_revision = "0012_conversation_position"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("ai_usage"):
        op.create_table(
            "ai_usage",
            sa.Column("id", sa.Uuid(), nullable=False),
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
            sa.UniqueConstraint("period", name="uq_ai_usage_period"),
        )


def downgrade() -> None:
    op.drop_table("ai_usage")
