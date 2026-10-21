"""Short chat titles for the Learn list, named after the first reply."""

import sqlalchemy as sa
from alembic import op

revision = "0033_session_titles"
down_revision = "0032_milestone_details"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("study_sessions")}
    if "title" not in columns:
        with op.batch_alter_table("study_sessions") as batch:
            batch.add_column(sa.Column("title", sa.String(80), nullable=True))


def downgrade():
    with op.batch_alter_table("study_sessions") as batch:
        batch.drop_column("title")
