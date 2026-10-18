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
    inspector = sa.inspect(op.get_bind())
    # Fresh installs get this FK from 0001's create_all baseline under the
    # dialect's default name (resources_study_session_id_fkey on Postgres).
    fk_names = [
        fk["name"] for fk in inspector.get_foreign_keys("resources")
        if fk["constrained_columns"] == ["study_session_id"] and fk["name"]
    ]
    indexes = {index["name"] for index in inspector.get_indexes("resources")}
    with op.batch_alter_table("resources") as batch:
        if "ix_resources_study_session_id" in indexes:
            batch.drop_index("ix_resources_study_session_id")
        for name in fk_names:
            batch.drop_constraint(name, type_="foreignkey")
        batch.drop_column("study_session_id")
