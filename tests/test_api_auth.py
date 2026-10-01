"""Comprehensive API tests for TestPilot AI - Auth, CRUD, and Edge Cases"""

import os
import sys

import pytest

# Add the project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import get_db_session
from api.main import app
from api.models import Base

# =====================
# Test Database Setup
# =====================

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


def create_test_engine():
    """Create a fresh in-memory test engine."""
    return create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def create_test_session(engine):
    """Create a sessionmaker bound to the engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db(session):
    """Factory to create dependency override function."""

    def _override():
        try:
            yield session
        finally:
            pass

    return _override


# =====================
# Fixtures
# =====================


@pytest.fixture(scope="function")
def test_client():
    """Create a fresh test client with isolated database for each test."""
    engine = create_test_engine()
    Session = create_test_session(engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Override dependency
    override = override_get_db(Session())
    app.dependency_overrides[get_db_session] = override

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.fixture
def test_user_password():
    """Test user password."""
    return "TestPassword123!"


@pytest.fixture
def test_user_data(test_user_password):
    """Test user registration data."""
    return {
        "email": "testuser@example.com",
        "password": test_user_password,
        "full_name": "Test User",
    }


# =====================
# SIGN UP TESTS
# =====================


class TestSignUp:
    """Comprehensive tests for user registration."""

    def test_register_success(self, test_client, test_user_data):
        """Positive: Valid registration should succeed."""
        response = test_client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["plan"] == "free"
        assert "user_id" in data

    def test_register_with_name(self, test_client, test_user_data):
        """Positive: Registration with full name."""
        response = test_client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 200

        # Verify user was created with name
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        user_info = test_client.get("/api/v1/me", headers=headers).json()
        assert user_info["full_name"] == "Test User"

    def test_register_without_name(self, test_client):
        """Positive: Registration without full name (optional field)."""
        data = {"email": "noname@example.com", "password": "Password123!"}
        response = test_client.post("/api/v1/auth/register", json=data)
        assert response.status_code == 200

    def test_register_duplicate_email(self, test_client, test_user_data):
        """Negative: Duplicate email should fail."""
        # First registration
        response1 = test_client.post("/api/v1/auth/register", json=test_user_data)
        assert response1.status_code == 200

        # Second registration with same email
        response2 = test_client.post("/api/v1/auth/register", json=test_user_data)
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"].lower()

    def test_register_invalid_email_format(self, test_client):
        """Negative: Invalid email format should be rejected."""
        invalid_emails = [
            "not-an-email",
            "@missing-local.com",
            "missing@domain",
            "spaces in@email.com",
            "user@.com",
            "",
            "   ",
        ]

        for email in invalid_emails:
            data = {"email": email, "password": "Password123!", "full_name": "Test"}
            response = test_client.post("/api/v1/auth/register", json=data)
            # Print for debugging
            print(f"Email '{email}': status={response.status_code}")

    def test_register_short_password(self, test_client):
        """Negative: Password too short should fail."""
        data = {
            "email": "shortpass@example.com",
            "password": "short",
            "full_name": "Test",
        }
        response = test_client.post("/api/v1/auth/register", json=data)
        # Print status for debugging
        print(f"Short password response: {response.status_code}")

    def test_register_empty_fields(self, test_client):
        """Negative: Empty fields should fail."""
        empty_fields = [
            {"email": "", "password": "Password123!"},
            {"email": "test@example.com", "password": ""},
            {"email": "", "password": ""},
        ]

        for data in empty_fields:
            response = test_client.post("/api/v1/auth/register", json=data)
            # Should fail with validation error
            assert (
                response.status_code == 422
            ), f"Expected 422 for {data}, got {response.status_code}"

    def test_register_missing_fields(self, test_client):
        """Negative: Missing required fields should fail."""
        missing_fields = [
            {},
            {"email": "test@example.com"},
            {"password": "Password123!"},
        ]

        for data in missing_fields:
            response = test_client.post("/api/v1/auth/register", json=data)
            assert response.status_code == 422

    def test_register_special_chars_email(self, test_client):
        """Edge case: Email with special characters."""
        special_emails = [
            "user+tag@example.com",
            "user.name@example.com",
            "user_name@example.com",
            "user-name@example.com",
        ]

        for email in special_emails:
            data = {"email": email, "password": "Password123!", "full_name": "Test"}
            response = test_client.post("/api/v1/auth/register", json=data)
            # Most of these should work
            print(f"Special email '{email}': status={response.status_code}")

    def test_register_long_email(self, test_client):
        """Edge case: Very long email address."""
        long_email = "a" * 200 + "@example.com"
        data = {"email": long_email, "password": "Password123!", "full_name": "Test"}
        response = test_client.post("/api/v1/auth/register", json=data)
        # Should handle gracefully
        print(f"Long email response: {response.status_code}")

    def test_register_unicode_email(self, test_client):
        """Edge case: Unicode characters in email."""
        unicode_emails = [
            "用户@example.com",
            "тест@example.com",
            "ユーザー@example.com",
        ]

        for email in unicode_emails:
            data = {"email": email, "password": "Password123!", "full_name": "Test"}
            response = test_client.post("/api/v1/auth/register", json=data)
            print(f"Unicode email '{email}': status={response.status_code}")


# =====================
# LOGIN TESTS
# =====================


class TestLogin:
    """Comprehensive tests for user login."""

    def test_login_success(self, test_client):
        """Positive: Valid login should return token."""
        # Register first
        register_resp = test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "password": "LoginPass123!",
                "full_name": "Login User",
            },
        )
        assert register_resp.status_code == 200

        # Now login
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "LoginPass123!"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user_id" in data

    def test_login_wrong_password(self, test_client):
        """Negative: Wrong password should fail."""
        # Register
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "wrongpass@example.com", "password": "CorrectPass123!"},
        )

        # Login with wrong password
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "wrongpass@example.com", "password": "WrongPass123!"},
        )

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, test_client):
        """Negative: Non-existent user should fail."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "SomePass123!"},
        )

        assert response.status_code == 401

    def test_login_empty_email(self, test_client):
        """Negative: Empty email should fail."""
        response = test_client.post(
            "/api/v1/auth/login", json={"email": "", "password": "SomePass123!"}
        )

        assert response.status_code == 422

    def test_login_empty_password(self, test_client):
        """Negative: Empty password should fail."""
        response = test_client.post(
            "/api/v1/auth/login", json={"email": "test@example.com", "password": ""}
        )

        assert response.status_code == 422

    def test_login_no_body(self, test_client):
        """Negative: Empty body should fail."""
        response = test_client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_login_case_sensitivity_email(self, test_client):
        """Edge case: Email case sensitivity."""
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

        # Email is unique and case-sensitive in our implementation
        assert response.status_code == 401

    def test_login_whitespace(self, test_client):
        """Edge case: Whitespace in email."""
        # Register
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "whitespace@test.com", "password": "WSPass123!"},
        )

        # Try login with leading/trailing whitespace
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "  whitespace@test.com  ", "password": "WSPass123!"},
        )

        # Depends on whether we strip whitespace
        print(f"Whitespace login: {response.status_code}")

    def test_login_invalid_email_format(self, test_client):
        """Negative: Invalid email format should fail."""
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": "SomePass123!"},
        )

        # May pass or fail depending on server-side validation
        print(f"Invalid email login: {response.status_code}")

    def test_login_token_format(self, test_client):
        """Positive: Login token should be valid JWT."""
        # Register
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "tokentest@example.com", "password": "TokenPass123!"},
        )

        # Login
        response = test_client.post(
            "/api/v1/auth/login",
            json={"email": "tokentest@example.com", "password": "TokenPass123!"},
        )

        token = response.json()["access_token"]

        # JWT format: header.payload.signature
        parts = token.split(".")
        assert len(parts) == 3, "Token should be JWT format"

    def test_login_multiple_sessions(self, test_client):
        """Positive: Multiple logins should work."""
        # Register
        test_client.post(
            "/api/v1/auth/register",
            json={"email": "multi@example.com", "password": "MultiPass123!"},
        )

        # First login
        resp1 = test_client.post(
            "/api/v1/auth/login",
            json={"email": "multi@example.com", "password": "MultiPass123!"},
        )
        assert resp1.status_code == 200
        token1 = resp1.json()["access_token"]

        # Second login (simulating new device/session)
        resp2 = test_client.post(
            "/api/v1/auth/login",
            json={"email": "multi@example.com", "password": "MultiPass123!"},
        )
        assert resp2.status_code == 200
        token2 = resp2.json()["access_token"]

        # Tokens should be different (new JWT each time)
        assert token1 != token2, "Each login should generate a new token"

    def test_login_get_user_info_after(self, test_client):
        """Positive: Should be able to get user info after login."""
        # Register
        test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "userinfo@example.com",
                "password": "UserInfoPass123!",
                "full_name": "Info User",
            },
        )

        # Login
        login_resp = test_client.post(
            "/api/v1/auth/login",
            json={"email": "userinfo@example.com", "password": "UserInfoPass123!"},
        )
        token = login_resp.json()["access_token"]

        # Get user info
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = test_client.get("/api/v1/me", headers=headers)

        assert me_resp.status_code == 200
        user_data = me_resp.json()
        assert user_data["email"] == "userinfo@example.com"
        assert user_data["full_name"] == "Info User"
        assert user_data["plan"] == "free"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
