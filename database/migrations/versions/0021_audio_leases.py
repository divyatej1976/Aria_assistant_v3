"""Add durable audio generation claims and crash recovery limits."""

import sqlalchemy as sa
from alembic import op

revision = "0021_audio_leases"
down_revision = "0020_chat_fallback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("audio_artifacts")}
    additions = (
        sa.Column("generation_token", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generation_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    for column in additions:
        if column.name not in columns:
            op.add_column("audio_artifacts", column)


def downgrade() -> None:
    with op.batch_alter_table("audio_artifacts") as batch:
        batch.drop_column("generation_attempts")
        batch.drop_column("lease_until")
        batch.drop_column("generation_token")
