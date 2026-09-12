"""Scope assessment idempotency per owner; dedupe learning activities.

- assessment_attempts.idempotency_key was globally unique (model unique=True)
  while the replay check is owner-scoped: two learners reusing a
  client-generated key caused an unhandled IntegrityError. Replaced by
  (owner_id, idempotency_key).
- learning_activities gains (owner_id, activity_type, occurred_on,
  source_id) uniqueness so concurrent requests cannot inflate counts.

Fresh databases build both tables from current metadata (0001 create_all),
so this migration only patches legacy Postgres databases that still carry
the old global unique constraint; every step is inspector-guarded.
"""

import sqlalchemy as sa
from alembic import op

revision = "0017_owner_scoped_idempotency"
down_revision = "0016_rate_limit_buckets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    attempts_uniques = {
        uq["name"] for uq in inspector.get_unique_constraints("assessment_attempts")
    }
    attempts_indexes = {ix["name"] for ix in inspector.get_indexes("assessment_attempts")}

    # Drop the legacy global unique (constraint form and/or index form).
    for legacy in ("assessment_attempts_idempotency_key_key",):
        if legacy in attempts_uniques:
            op.drop_constraint(legacy, "assessment_attempts", type_="unique")
    if "ix_assessment_attempts_idempotency_key" in attempts_indexes:
        op.drop_index(
            "ix_assessment_attempts_idempotency_key", table_name="assessment_attempts"
        )

    if "uq_attempt_owner_idempotency" not in attempts_uniques:
        op.create_index(
            "ix_assessment_attempts_idempotency_key",
            "assessment_attempts",
            ["idempotency_key"],
            unique=False,
        )
        op.create_unique_constraint(
            "uq_attempt_owner_idempotency",
            "assessment_attempts",
            ["owner_id", "idempotency_key"],
        )

    activity_uniques = {
        uq["name"] for uq in inspector.get_unique_constraints("learning_activities")
    }
    if "uq_learning_activity_owner_type_day_source" not in activity_uniques:
        op.create_unique_constraint(
            "uq_learning_activity_owner_type_day_source",
            "learning_activities",
            ["owner_id", "activity_type", "occurred_on", "source_id"],
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    activity_uniques = {
        uq["name"] for uq in inspector.get_unique_constraints("learning_activities")
    }
    if "uq_learning_activity_owner_type_day_source" in activity_uniques:
        op.drop_constraint(
            "uq_learning_activity_owner_type_day_source", "learning_activities", type_="unique"
        )
    attempts_uniques = {
        uq["name"] for uq in inspector.get_unique_constraints("assessment_attempts")
    }
    if "uq_attempt_owner_idempotency" in attempts_uniques:
        op.drop_constraint(
            "uq_attempt_owner_idempotency", "assessment_attempts", type_="unique"
        )
    op.drop_index(
        "ix_assessment_attempts_idempotency_key", table_name="assessment_attempts"
    )
    op.create_index(
        "ix_assessment_attempts_idempotency_key",
        "assessment_attempts",
        ["idempotency_key"],
        unique=True,
    )
