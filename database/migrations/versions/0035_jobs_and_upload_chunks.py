"""Background jobs that many workers run in parallel, and pieces of large uploads."""

import sqlalchemy as sa
from alembic import op

revision = "0035_jobs_and_upload_chunks"
down_revision = "0034_digest_and_audio_style"
branch_labels = None
depends_on = None


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "jobs" not in tables:
        op.create_table(
            "jobs",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("kind", sa.String(32), nullable=False),
            sa.Column("target_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("status", sa.String(16), nullable=False, server_default="queued", index=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("progress", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if "upload_chunks" not in tables:
        op.create_table(
            "upload_chunks",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("upload_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("seq", sa.Integer(), nullable=False),
            sa.Column("data", sa.LargeBinary(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade():
    op.drop_table("upload_chunks")
    op.drop_table("jobs")
