from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

db_url = get_settings().database_url
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)

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
