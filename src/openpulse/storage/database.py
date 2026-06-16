"""Database engine and session management."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine(database_url: str | None = None) -> Engine:
    """
    Get or create the SQLAlchemy engine.

    Args:
        database_url: Database connection URL. If None, uses the default SQLite path.

    Returns:
        SQLAlchemy Engine instance.
    """
    global _engine

    if _engine is not None and database_url is None:
        return _engine

    if database_url is None:
        # Default SQLite path
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:
            base = Path.home() / ".openpulse"
        db_path = base / "openpulse.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{db_path}"

    # Handle SQLite URL with ~ expansion
    if database_url.startswith("sqlite:///~/"):
        db_path = Path.home() / database_url.replace("sqlite:///~/", "")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{db_path}"

    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_engine(
        database_url,
        echo=False,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
    return _engine


def get_session_factory(engine: Engine | None = None) -> sessionmaker:
    """Get or create a session factory."""
    global _SessionLocal

    if _SessionLocal is not None and engine is None:
        return _SessionLocal

    if engine is None:
        engine = get_engine()

    _SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    return _SessionLocal


def get_session() -> Session:
    """Get a new database session."""
    factory = get_session_factory()
    return factory()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with session_scope() as session:
            session.add(obj)
            session.commit()
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Engine | None = None) -> None:
    """Create all database tables."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(bind=engine)


def reset_db_state() -> None:
    """Reset global engine and session state (useful for testing)."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
