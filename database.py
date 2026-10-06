"""
database.py - SQLite connection and SQLAlchemy session management.

The SQLite database is the single datastore for both:
1. Original Dashboard / Tasks / DSA Tracker
2. Software + Cloud Engineer Tracker

The module supports both:
    uvicorn main:app --reload

and package-style imports.
"""

from __future__ import annotations

import os
from typing import Any, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# =============================================================================
# Database configuration
# =============================================================================

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "sqlite:///./devops_tracker.db",
)

_connect_args: dict[str, object] = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)


engine: Engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    future=True,
)


# =============================================================================
# SQLite foreign-key enforcement
# =============================================================================

@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(
    dbapi_connection: Any,
    _connection_record: Any,
) -> None:
    """
    SQLite does not enforce FOREIGN KEY constraints by default.

    Enable them for every SQLite connection.
    """
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()

        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()


# =============================================================================
# SQLAlchemy session factory
# =============================================================================

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


# =============================================================================
# SQLAlchemy declarative base
# =============================================================================

class Base(DeclarativeBase):
    """
    Declarative base shared by every ORM model.
    """
    pass


# =============================================================================
# FastAPI database dependency
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency.

    Creates one database session for a request and guarantees
    that the session is closed afterwards.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Database initialization
# =============================================================================

def init_db() -> None:
    """
    Create all database tables.

    Both the original tracker models and the newer Software +
    Cloud Engineer models must be imported before create_all()
    so SQLAlchemy knows about every table.

    The imports support both package mode and direct/root mode.
    """

    # -------------------------------------------------------------------------
    # Original Dashboard / Tasks / DSA models
    # -------------------------------------------------------------------------
    try:
        from . import models  # noqa: F401
    except ImportError:
        import models  # noqa: F401

    # -------------------------------------------------------------------------
    # New Software + Cloud Engineer models
    # -------------------------------------------------------------------------
    #
    # Older copies of the project may not contain feature_models.py.
    # Therefore this import is optional so the original tracker can still
    # start if that file has not yet been added.
    #
    try:
        from . import feature_models  # noqa: F401
    except ImportError:
        try:
            import feature_models  # noqa: F401
        except ImportError:
            feature_models = None

    # -------------------------------------------------------------------------
    # Create all registered tables.
    #
    # create_all() is idempotent:
    # existing tables are preserved.
    # -------------------------------------------------------------------------
    Base.metadata.create_all(bind=engine)
