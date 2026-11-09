"""Local-first SQLAlchemy engine factory. No database is opened at import time."""

from pathlib import Path
import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def default_database_url() -> str:
    """Use a user-owned data directory, never the public repository checkout."""
    base = Path(os.environ.get("TRAPLINE_DATA_DIR", Path.home() / ".local" / "share" / "trapline"))
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    return f"sqlite:///{base / 'trapline.db'}"


def make_engine(url: str | None = None) -> Engine:
    target = url or os.environ.get("TRAPLINE_DATABASE_URL") or default_database_url()
    engine = create_engine(target, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
