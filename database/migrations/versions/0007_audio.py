"""Add audio artifacts and playback progress."""

import sqlalchemy as sa
from alembic import op

revision = "0007_audio"
down_revision = "0006_planner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("audio_artifacts"):
        op.create_table(
            "audio_artifacts",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("source_type", sa.String(length=16), nullable=False),
            sa.Column("source_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
            sa.Column("error_detail", sa.Text(), nullable=True),
            sa.Column("audio_bytes", sa.LargeBinary(), nullable=True),
            sa.Column("content_type", sa.String(length=64), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("storage_key", sa.String(length=500), nullable=True),
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
        )
    if not inspector.has_table("audio_progress"):
        op.create_table(
            "audio_progress",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("artifact_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("position_seconds", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
            sa.ForeignKeyConstraint(["artifact_id"], ["audio_artifacts.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("owner_id", "artifact_id", name="uq_audio_progress_artifact"),
        )


def downgrade() -> None:
    op.drop_table("audio_progress")
    op.drop_table("audio_artifacts")
