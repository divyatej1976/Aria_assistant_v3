"""Durable message actions; SQLite graph checkpoints use the pinned saver schema."""

import sqlite3

import sqlalchemy as sa
from alembic import op

revision = "0027_brain_actions"
down_revision = "0026_daily_review"
branch_labels = None
depends_on = None


def upgrade():
    from app.db.models import BrainAction

    bind = op.get_bind()
    BrainAction.__table__.create(bind, checkfirst=True)
    if "action" not in {c["name"] for c in sa.inspect(bind).get_columns("conversation_messages")}:
        with op.batch_alter_table("conversation_messages") as batch:
            batch.add_column(sa.Column("action", sa.JSON(), nullable=True))
    # The SQLite saver owns a separate database, not ARIA's transactional
    # connection. Its setup uses executescript/PRAGMA and cannot participate
    # in the application's Alembic transaction. Never run this on that connection.
    if bind.dialect.name == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver

        from app.core.config import get_settings

        with sqlite3.connect(get_settings().aria_brain_checkpoint_path) as connection:
            SqliteSaver(connection).setup()


def downgrade():
    with op.batch_alter_table("conversation_messages") as batch:
        batch.drop_column("action")
    op.drop_table("brain_actions")
    # Retain separately owned checkpoints on rollback; never discard action
    # recovery history as a side effect of rolling back application schema.
