"""Add generalized idempotency keys for consequential operations."""

import sqlalchemy as sa
from alembic import op

revision = "0010_idempotency"
down_revision = "0009_push"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("idempotency_keys"):
        op.create_table(
            "idempotency_keys",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("scope", sa.String(length=64), nullable=False),
            sa.Column("key", sa.String(length=128), nullable=False),
            sa.Column("response_status", sa.Integer(), nullable=True),
            sa.Column("response_json", sa.JSON(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
            sa.UniqueConstraint(
                "owner_id", "scope", "key", name="uq_idempotency_owner_scope_key"
            ),
        )


def downgrade() -> None:
    op.drop_table("idempotency_keys")
