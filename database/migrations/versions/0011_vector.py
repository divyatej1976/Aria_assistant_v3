"""Add a pgvector embedding column + HNSW index to resource_chunks (Postgres).

SQLite is skipped so the shared test/dev path keeps working. Backfills the
vector column from the JSON embeddings already stored at ingestion. The column
dimension must match ARIA_EMBEDDING_DIM (default 768) so deterministic and
cloud embeddings stay index-compatible.
"""

import os

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0011_vector"
down_revision = "0010_idempotency"
branch_labels = None
depends_on = None


def _dimension() -> int:
    return int(os.environ.get("ARIA_EMBEDDING_DIM", "768"))


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("resource_chunks")}
    if "embedding" not in columns:
        op.add_column("resource_chunks", sa.Column("embedding", Vector(_dimension())))
    indexes = {index["name"] for index in inspector.get_indexes("resource_chunks")}
    if "ix_resource_chunks_embedding_hnsw" not in indexes:
        op.create_index(
            "ix_resource_chunks_embedding_hnsw",
            "resource_chunks",
            ["embedding"],
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        )
    op.execute(
        sa.text(
            "UPDATE resource_chunks "
            "SET embedding = regexp_replace(embedding_json::text, '\\s', '', 'g')::vector "
            "WHERE json_array_length(embedding_json) = :dim"
        ).bindparams(dim=_dimension())
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.drop_index("ix_resource_chunks_embedding_hnsw", table_name="resource_chunks")
    op.drop_column("resource_chunks", "embedding")
