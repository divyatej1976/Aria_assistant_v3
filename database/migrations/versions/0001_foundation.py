"""Create the ARIA baseline schema.

Squashed baseline: because the schema is created from the current ORM metadata,
the original 0002-0006 ALTER migrations duplicated columns that 0001 already
created. This single baseline is metadata-driven, so it always matches the
models. No database was ever deployed against the old chain.
"""

from alembic import op

from app.db.base import Base
from app.db import models  # noqa: F401

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

