"""Database configuration and session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from .models import Base

# Database URL from environment or default to SQLite for testing
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    os.getenv("TEST_DATABASE_URL", "sqlite:///./testpilot.db")
)

# Use in-memory SQLite for testing if TESTING environment variable is set
if os.getenv("TESTING"):
    DATABASE_URL = "sqlite:///:memory:"

# Create engine — pool tuning only applies to Postgres, not SQLite
_engine_kwargs: dict = {"pool_pre_ping": True}
if "sqlite" not in DATABASE_URL:
    _engine_kwargs.update(pool_size=10, max_overflow=20, pool_recycle=3600)
engine = create_engine(DATABASE_URL, **_engine_kwargs)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database - create all tables."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")


@contextmanager
def get_db():
    """Get database session context manager."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session():
    """Get database session (for Dependency Injection)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Import models to ensure they're registered
from . import models  # noqa: E402
