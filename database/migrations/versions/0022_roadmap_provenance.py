"""Preserve application-controlled roadmap generation provenance."""

import sqlalchemy as sa
from alembic import op

revision = "0022_roadmap_provenance"
down_revision = "0021_audio_leases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("roadmaps")}
    for column in (
        sa.Column("generation_mode", sa.String(16), nullable=True),
        sa.Column("fallback_reason", sa.String(32), nullable=True),
    ):
        if column.name not in columns:
            op.add_column("roadmaps", column)


def downgrade() -> None:
    with op.batch_alter_table("roadmaps") as batch:
        batch.drop_column("fallback_reason")
        batch.drop_column("generation_mode")
