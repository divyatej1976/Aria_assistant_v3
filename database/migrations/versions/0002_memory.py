"""Add learner memory tables: preferences and concept relations.

The 0001 baseline is metadata-driven (Base.metadata.create_all), so on a
fresh database these tables already exist and this migration is a no-op.
On a database that was migrated before these models existed, this creates
the missing tables. Each create is guarded accordingly.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_memory"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("learner_preferences"):
        op.create_table(
            "learner_preferences",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("key", sa.String(length=64), nullable=False),
            sa.Column("value", sa.String(length=500), nullable=False),
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
            sa.UniqueConstraint("owner_id", "key", name="uq_learner_preference_key"),
        )
    if not inspector.has_table("concept_relations"):
        op.create_table(
            "concept_relations",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("owner_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("concept_id", sa.Uuid(), nullable=False, index=True),
            sa.Column("prerequisite_concept_id", sa.Uuid(), nullable=False, index=True),
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
            sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"]),
            sa.ForeignKeyConstraint(["prerequisite_concept_id"], ["concepts.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "concept_id", "prerequisite_concept_id", name="uq_concept_relation"
            ),
        )


def downgrade() -> None:
    op.drop_table("concept_relations")
    op.drop_table("learner_preferences")
