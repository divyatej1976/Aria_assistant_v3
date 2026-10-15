"""Remember which reply depth the tutor used, for the per-reply depth badge."""

import sqlalchemy as sa
from alembic import op

revision = "0028_response_depth"
down_revision = "0027_brain_actions"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("conversation_messages")}
    if "response_depth" not in columns:
        with op.batch_alter_table("conversation_messages") as batch:
            batch.add_column(sa.Column("response_depth", sa.String(16), nullable=True))


def downgrade():
    with op.batch_alter_table("conversation_messages") as batch:
        batch.drop_column("response_depth")
