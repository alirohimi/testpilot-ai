"""Database configuration and session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from .models import Base

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://testpilot:testpilot@localhost:5432/testpilot"
)

# Fallback for development
if DATABASE_URL == "postgresql://testpilot:testpilot@localhost:5432/testpilot":
    print("⚠️  Using default database URL. Set DATABASE_URL environment variable for production.")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

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
