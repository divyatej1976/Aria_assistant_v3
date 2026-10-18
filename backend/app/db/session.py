from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

db_url = get_settings().database_url
connect_args = {}
pool_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}
else:
    # Async routes check out connections on the event loop, so a long wait for
    # a free connection stalls every request: fail fast instead of queueing 30s.
    pool_args = {"pool_size": 10, "max_overflow": 10, "pool_timeout": 5}

engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args, **pool_args)

if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
        except Exception:
            pass
        finally:
            cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def release_connection(db: Session) -> None:
    """End the session's transaction before a slow await (LLM, embeddings).

    Otherwise the pooled connection sits idle-in-transaction for the whole
    provider call. Objects stay usable (expire_on_commit=False) and the next
    query opens a new transaction. Unflushed changes are left alone so a
    half-built unit of work is never committed early.
    """
    if db.in_transaction() and not (db.new or db.dirty or db.deleted):
        db.commit()
