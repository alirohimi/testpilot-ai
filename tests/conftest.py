"""Conftest.py - Shared fixtures and configuration for all tests"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from api.database import get_db_session, engine
from api.models import Base

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# ---------------------------------------------------------------------------
# Database fixtures (shared across all test modules)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped test database engine."""
    eng = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def test_session(test_engine):
    """Per-test database session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_session):
    """Test client with database override."""
    def override_get_db():
        try:
            yield test_session
        finally:
            pass

    # Save any existing override (e.g. the session-scoped e2e_server) so we
    # don't clobber shared test state when this function-scoped fixture ends.
    previous = app.dependency_overrides.get(get_db_session)
    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as c:
        yield c
    # Restore rather than clear, preserving any session-scoped override.
    if previous is not None:
        app.dependency_overrides[get_db_session] = previous
    else:
        app.dependency_overrides.pop(get_db_session, None)


# ---------------------------------------------------------------------------
# Local E2E test server (for test_frontend_e2e_local.py)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def e2e_server(test_engine):
    """In-process server for local E2E tests — no subprocess needed."""
    # Override DB for the server too
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_get_db
    Base.metadata.create_all(bind=test_engine)

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth / user fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_password():
    """Standard test password."""
    return "TestPassword123!"


@pytest.fixture
def user_data(test_password):
    """Standard user registration data."""
    return {
        "email": "test@example.com",
        "password": test_password,
        "full_name": "Test User"
    }


@pytest.fixture
def registered_user(client, user_data, request):
    """Register a user with unique email per test to avoid shared DB state."""
    unique_email = f"{request.node.name}@example.com"
    data = user_data.copy()
    data["email"] = unique_email
    response = client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 200
    resp_data = response.json()
    return {
        "token": resp_data["access_token"],
        "user_id": resp_data["user_id"],
        "email": unique_email,
        "password": user_data["password"]
    }


@pytest.fixture
def auth_headers(registered_user):
    """Authentication headers."""
    return {"Authorization": f"Bearer {registered_user['token']}"}


@pytest.fixture
def api_key_with_headers(client, auth_headers):
    """Create API key and return both key and headers."""
    response = client.post("/api/v1/keys",
                           json={"name": "Test Key", "tier": "free"},
                           headers=auth_headers)
    assert response.status_code in (200, 201)
    return {
        "key": response.json()["key"],
        "headers": auth_headers
    }
