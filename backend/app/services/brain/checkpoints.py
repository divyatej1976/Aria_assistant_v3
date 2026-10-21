"""Database-specific checkpoint storage; no learner content is stored here."""

from contextlib import asynccontextmanager

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from sqlalchemy.engine import make_url

from app.core.config import get_settings


def postgres_uri(url):
    # psycopg accepts a PostgreSQL URI, not SQLAlchemy's +psycopg scheme.
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


def setup_postgres_checkpoints(url):
    """Run the saver's migrations once at startup, serialized across workers.

    The saver needs autocommit (including concurrent index creation), so it
    must not share an application transaction or Alembic connection.
    """
    import psycopg
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg.rows import dict_row

    with psycopg.connect(postgres_uri(url), autocommit=True, row_factory=dict_row) as connection:
        connection.execute("SELECT pg_advisory_lock(7005)")
        try:
            PostgresSaver(connection).setup()
        finally:
            connection.execute("SELECT pg_advisory_unlock(7005)")


@asynccontextmanager
async def checkpoint_saver(db):
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncPostgresSaver.from_conn_string(
            postgres_uri(bind.url), serde=JsonPlusSerializer(allowed_msgpack_modules=())
        ) as saver:
            yield saver
    else:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        async with AsyncSqliteSaver.from_conn_string(get_settings().aria_brain_checkpoint_path) as saver:
            saver.serde = JsonPlusSerializer(allowed_msgpack_modules=())
            yield saver
