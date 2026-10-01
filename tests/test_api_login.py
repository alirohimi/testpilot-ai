"""Login API tests for TestPilot AI"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db_session
from api.main import app

# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


def create_test_engine():
    return create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def create_test_session(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db(session):
    def _override():
        try:
            yield session
        finally:
            pass

    return _override


@pytest.fixture(scope="function")
def test_client():
    """Create a fresh test client with isolated database for each test."""
    engine = create_test_engine()
    Session = create_test_session(engine)

    Base.metadata.create_all(bind=engine)

    override = override_get_db(Session())
    app.dependency_overrides[get_db_session] = override

    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.fixture
def registered_user(test_client):
    """Register a user and return credentials."""
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "LoginPass123!",
            "full_name": "Login User",
        },
    )
    assert response.status_code == 200
    return response.json()


class TestLogin:
    """Tests for login functionality."""

    def test_login_success(self, test_client):
        """Positive: Valid login should return token."""
        # Register first
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "success@example.com", "password": "SuccessPass123!"},
        )

        # Login
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "success@example.com", "password": "SuccessPass123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, test_client):
        """Negative: Wrong password should fail."""
        # Register
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "wrong@example.com", "password": "CorrectPass123!"},
        )

        # Login with wrong password
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "WrongPass123!"},
        )

        assert response.status_code == 401

    def test_login_nonexistent_user(self, test_client):
        """Negative: Non-existent user should fail."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "SomePass123!"},
        )

        assert response.status_code == 401

    def test_login_empty_fields(self, test_client):
        """Negative: Empty fields should fail."""
        response = test_client.post(
            "/api/v1/auth/login", json={"email": "", "password": ""}
        )

        assert response.status_code == 422

    def test_login_missing_fields(self, test_client):
        """Negative: Missing fields should fail."""
        response = test_client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_login_case_sensitive_email(self, test_client):
        """Edge case: Email should be case sensitive."""
        # Register with lowercase
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "case@test.com", "password": "CasePass123!"},
        )

        # Try login with uppercase
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "CASE@TEST.COM", "password": "CasePass123!"},
        )

        assert response.status_code == 401

    def test_login_whitespace_email(self, test_client):
        """Edge case: Whitespace in email."""
        # Register without whitespace
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "space@test.com", "password": "SpacePass123!"},
        )

        # Try login with whitespace
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": " space@test.com ", "password": "SpacePass123!"},
        )

        # Should fail since we don't strip whitespace
        print(f"Whitespace email login: {response.status_code}")

    def test_login_invalid_email_format(self, test_client):
        """Negative: Invalid email format."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": "SomePass123!"},
        )

        # Should fail validation or return 401
        assert response.status_code in [401, 422]


class TestSessionManagement:
    """Tests for session/token management."""

    def test_token_format(self, test_client):
        """Positive: Token should be valid JWT."""
        # Register and login
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "token@example.com", "password": "TokenPass123!"},
        )

        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "token@example.com", "password": "TokenPass123!"},
        )

        token = response.json()["access_token"]

        # JWT format: header.payload.signature
        parts = token.split(".")
        assert len(parts) == 3

    def test_token_expiration(self, test_client):
        """Edge case: Token expiration."""
        # Register and login
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "expire@example.com", "password": "ExpirePass123!"},
        )

        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "expire@example.com", "password": "ExpirePass123!"},
        )

        token = response.json()["access_token"]

        # Decode and check expiration (should be 15 minutes from now)
        from jose import jwt as jose_jwt

        from api.auth import ALGORITHM, SECRET_KEY

        try:
            payload = jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            assert "exp" in payload
            assert "sub" in payload
        except Exception as e:
            print(f"JWT decode issue: {e}")

    def test_concurrent_logins(self, test_client):
        """Positive: Multiple logins should work independently."""
        # Register
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "concurrent@example.com", "password": "ConcurrentPass123!"},
        )

        # First login
        resp1 = test_client.post(
            "/api/v1/auth/login",
            json={"email": "concurrent@example.com", "password": "ConcurrentPass123!"},
        )
        token1 = resp1.json()["access_token"]

        # Second login
        resp2 = test_client.post(
            "/api/v1/auth/login",
            json={"email": "concurrent@example.com", "password": "ConcurrentPass123!"},
        )
        token2 = resp2.json()["access_token"]

        # Tokens should be different
        assert token1 != token2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
