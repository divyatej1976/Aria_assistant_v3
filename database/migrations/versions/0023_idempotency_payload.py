"""Bind workflow idempotency keys to canonical request payloads."""

import sqlalchemy as sa
from alembic import op

revision = "0023_idempotency_payload"
down_revision = "0022_roadmap_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("idempotency_keys")}
    if "request_fingerprint" not in columns:
        op.add_column("idempotency_keys", sa.Column("request_fingerprint", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("idempotency_keys") as batch:
        batch.drop_column("request_fingerprint")
