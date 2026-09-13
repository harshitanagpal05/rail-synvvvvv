"""RailSync 2.0 — SQLAlchemy engine and session factory for Supabase PostgreSQL."""

from __future__ import annotations

from sqlalchemy import create_engine, event, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("db")

# Compile Postgres JSONB as TEXT in SQLite for local / fallback execution
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = settings.supabase_database_url
        if not db_url:
            db_url = "sqlite:///railsync.db"
            log.info("SUPABASE_DATABASE_URL not set; defaulting to local SQLite: %s", db_url)

        if db_url.startswith("sqlite"):
            _engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                echo=False,
            )
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

            from app.db.models import Base
            Base.metadata.create_all(bind=_engine)
            log.info("SQLite database initialized and schema created")
        else:
            _engine = create_engine(
                db_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False,
            )
            log.info("Database engine created")
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def get_db() -> Session:
    """FastAPI dependency — yields a DB session, closes on request end."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def check_db_health() -> bool:
    try:
        with get_session_factory()() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        log.warning("Database health check failed: %s", exc)
        return False
