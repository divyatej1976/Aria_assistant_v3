"""Durable workflow checkpoint for uncertain process-crash outcomes."""

import sqlalchemy as sa
from alembic import op

revision = "0025_workflow_checkpoint"
down_revision = "0024_concept_sync_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("idempotency_keys")}
    if "workflow_id" not in columns:
        op.add_column("idempotency_keys", sa.Column("workflow_id", sa.Uuid(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("idempotency_keys") as batch:
        batch.drop_column("workflow_id")
