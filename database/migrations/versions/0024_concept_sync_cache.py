"""Internal concept extraction cache, separate from user configuration."""

import sqlalchemy as sa
from alembic import op

revision = "0024_concept_sync_cache"
down_revision = "0023_idempotency_payload"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("learning_contexts")}
    for name, kind in (("concept_sync_fingerprint", sa.String(64)), ("concept_sync_names", sa.JSON())):
        if name not in columns:
            op.add_column("learning_contexts", sa.Column(name, kind, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("learning_contexts") as batch:
        batch.drop_column("concept_sync_names")
        batch.drop_column("concept_sync_fingerprint")
