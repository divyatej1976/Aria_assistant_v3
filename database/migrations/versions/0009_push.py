"""Add web push subscription table for push notifications."""

import sqlalchemy as sa
from alembic import op

revision = "0009_push"
down_revision = "0008_orchestration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("push_subscriptions"):
        op.create_table(
            "push_subscriptions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("endpoint", sa.Text(), nullable=False),
            sa.Column("p256dh", sa.Text(), nullable=False),
            sa.Column("auth", sa.Text(), nullable=False),
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
            sa.UniqueConstraint("endpoint", name="uq_push_subscription_endpoint"),
        )


def downgrade() -> None:
    op.drop_table("push_subscriptions")
