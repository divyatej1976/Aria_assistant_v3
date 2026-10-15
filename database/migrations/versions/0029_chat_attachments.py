"""Files attached in a chat belong to that chat; NULL keeps them in the library."""

import sqlalchemy as sa
from alembic import op

revision = "0029_chat_attachments"
down_revision = "0028_response_depth"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("resources")}
    if "study_session_id" not in columns:
        with op.batch_alter_table("resources") as batch:
            batch.add_column(sa.Column("study_session_id", sa.Uuid(), nullable=True))
            batch.create_foreign_key(
                "fk_resources_study_session_id", "study_sessions", ["study_session_id"], ["id"]
            )
            batch.create_index("ix_resources_study_session_id", ["study_session_id"])


def downgrade():
    # Existing chat files become library files again, which is how they behaved before.
    with op.batch_alter_table("resources") as batch:
        batch.drop_index("ix_resources_study_session_id")
        batch.drop_constraint("fk_resources_study_session_id", type_="foreignkey")
        batch.drop_column("study_session_id")
