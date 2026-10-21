"""A condensed digest of long files, and the chosen voice style of each audio episode."""

import sqlalchemy as sa
from alembic import op

revision = "0034_digest_and_audio_style"
down_revision = "0033_session_titles"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "digest" not in {c["name"] for c in inspector.get_columns("resources")}:
        with op.batch_alter_table("resources") as batch:
            batch.add_column(sa.Column("digest", sa.Text(), nullable=True))
    if "style" not in {c["name"] for c in inspector.get_columns("audio_artifacts")}:
        with op.batch_alter_table("audio_artifacts") as batch:
            batch.add_column(sa.Column("style", sa.String(16), nullable=True))


def downgrade():
    with op.batch_alter_table("audio_artifacts") as batch:
        batch.drop_column("style")
    with op.batch_alter_table("resources") as batch:
        batch.drop_column("digest")
