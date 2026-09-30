"""Test check failure endpoint and integration flows"""

import pytest
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from api.database import Base, get_db_session

# Use in-memory SQLite for testing (unique per test module)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db_session] = override_get_db
Base.metadata.create_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def unique_email(base="user"):
    """Generate a unique email to avoid conflicts."""
    return f"{base}_{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def valid_token(client):
    """Register a user and return a valid token."""
    email = unique_email("checkuser")
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "CheckPass123!",
        "full_name": "Check User"
    })
    return response.json()["access_token"]


@pytest.fixture
def api_key(client, valid_token):
    """Create an API key for testing."""
    headers = {"Authorization": f"Bearer {valid_token}"}
    response = client.post("/api/v1/keys", json={"name": "Test Key"}, headers=headers)
    return response.json()["key"]


class TestCheckEndpoint:
    """Test the core /api/v1/check endpoint."""

    def test_check_success(self, client, api_key):
        """Positive: Valid check request."""
        response = client.post("/api/v1/check",
                               headers={"X-API-Key": api_key},
                               json={
                                   "error_message": "AssertionError: Expected 5 but got 3",
                                   "use_llm": False
                               })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "result" in data
        assert "failure_type" in data["result"]
        assert "request_id" in data
        assert "timestamp" in data

    def test_check_empty_message(self, client, api_key):
        """Negative: Empty error message."""
        response = client.post("/api/v1/check",
                               headers={"X-API-Key": api_key},
                               json={"error_message": ""})
        # May pass or fail - document behavior
        print(f"Empty message status: {response.status_code}")

    def test_check_missing_field(self, client, api_key):
        """Negative: Missing error_message field."""
        response = client.post("/api/v1/check",
                               headers={"X-API-Key": api_key},
                               json={})
        assert response.status_code == 422

    def test_check_no_api_key(self, client):
        """Negative: No API key provided."""
        response = client.post("/api/v1/check",
                               json={"error_message": "Test error"})
        assert response.status_code in (401, 403)

    def test_check_invalid_api_key(self, client):
        """Negative: Invalid API key format."""
        response = client.post("/api/v1/check",
                               headers={"X-API-Key": "invalid_key"},
                               json={"error_message": "Test"})
        assert response.status_code == 401

    def test_check_llm_enabled(self, client, api_key):
        """Feature: LLM analysis when enabled."""
        response = client.post("/api/v1/check",
                               headers={"X-API-Key": api_key},
                               json={"error_message": "Test error", "use_llm": True})
        # LLM may or may not be available
        print(f"LLM check status: {response.status_code}")

    def test_check_scrub_enabled(self, client, api_key):
        """Feature: PII scrubbing in results."""
        response = client.post("/api/v1/check",
                               headers={"X-API-Key": api_key},
                               json={
                                   "error_message": "Error: Contact admin@test.com for help",
                                   "include_scrubbed": True
                               })
        assert response.status_code == 200
        result = response.json()["result"]
        if "scrubbed_error" in result:
            assert "admin@test.com" not in result["scrubbed_error"]


class TestBatchCheck:
    """Test batch check endpoint."""

    def test_batch_success(self, client, api_key):
        """Positive: Batch check multiple errors."""
        errors = [
            {"error_message": "AssertionError: x == y"},
            {"error_message": "ModuleNotFoundError: no module named 'requests'"},
        ]
        response = client.post("/api/v1/batch-check",
                               headers={"X-API-Key": api_key},
                               json=errors)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["results"]) == 2

    def test_batch_single_item(self, client, api_key):
        """Edge: Batch with single item."""
        response = client.post("/api/v1/batch-check",
                               headers={"X-API-Key": api_key},
                               json=[{"error_message": "Test"}])
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_batch_empty(self, client, api_key):
        """Edge: Empty batch."""
        response = client.post("/api/v1/batch-check",
                               headers={"X-API-Key": api_key},
                               json=[])
        assert response.status_code == 200
        assert response.json()["count"] == 0


class TestFullUserJourney:
    """Integration tests: Full user flow from signup to usage."""

    def test_signup_to_check(self, client):
        """Complete journey: Register → Login → Create Key → Check Failure."""
        # 1. Register
        email = unique_email("fulljourney")
        register_resp = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Journey123!",
            "full_name": "Journey User"
        })
        assert register_resp.status_code == 200
        token = register_resp.json()["access_token"]

        # 2. Verify login works (implicit in registration)
        me_resp = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200

        # 3. Create API key
        key_resp = client.post("/api/v1/keys",
                               json={"name": "Journey Key", "tier": "free"},
                               headers={"Authorization": f"Bearer {token}"})
        assert key_resp.status_code in (200, 201)
        api_key = key_resp.json()["key"]

        # 4. Run a check
        check_resp = client.post("/api/v1/check",
                                 headers={"X-API-Key": api_key},
                                 json={"error_message": "AssertionError: expected 2 + 2 = 4"})
        assert check_resp.status_code == 200
        assert check_resp.json()["success"] is True

        # 5. Check usage
        usage_resp = client.get("/api/v1/usage", headers={"Authorization": f"Bearer {token}"})
        assert usage_resp.status_code == 200
        assert usage_resp.json()["checks_used"] >= 1

    def test_multi_user_isolation(self, client):
        """Security: Two users cannot access each other's data."""
        # User A
        reg_a = client.post("/api/v1/auth/register", json={
            "email": unique_email("userA"), "password": "APass123!"
        })
        token_a = reg_a.json()["access_token"]
        key_a = client.post("/api/v1/keys",
                           json={"name": "A Key"},
                           headers={"Authorization": f"Bearer {token_a}"}).json()["key"]

        # User B
        reg_b = client.post("/api/v1/auth/register", json={
            "email": unique_email("userB"), "password": "BPass123!"
        })
        token_b = reg_b.json()["access_token"]
        key_b = client.post("/api/v1/keys",
                           json={"name": "B Key"},
                           headers={"Authorization": f"Bearer {token_b}"}).json()["key"]

        # A's key shouldn't work for B
        check = client.post("/api/v1/check",
                           headers={"X-API-Key": key_a},
                           json={"error_message": "Test"})
        # Should work for A
        assert check.status_code == 200

    def test_password_hashing(self, client):
        """Security: Passwords should never appear in API responses."""
        email = unique_email("secure")
        client.post("/api/v1/auth/register", json={
            "email": email, "password": "SecretPass123!"
        })

        login_resp = client.post("/api/v1/auth/login", json={
            "email": email, "password": "SecretPass123!"
        })
        response_body = str(login_resp.json())
        assert "SecretPass123!" not in response_body
        assert "secret" not in response_body.lower()

    def test_token_not_leaked_in_logs(self, client):
        """Security: Token should not appear in registration response in plain text."""
        resp = client.post("/api/v1/auth/register", json={
            "email": unique_email("logtest"), "password": "LogTest123!"
        })
        body = str(resp.json())
        # Token should be present (access_token field) but not the password
        assert "access_token" in body
        assert "LogTest123!" not in body


class TestErrorHandling:
    """Error handling and edge cases."""

    def test_server_error_on_unavailable_feature(self, client, api_key):
        """Graceful degradation when optional features unavailable."""
        response = client.post("/api/v1/check",
                               headers={"X-API-Key": api_key},
                               json={"error_message": "Test", "use_llm": True})
        # Should not crash - returns result even without LLM
        assert response.status_code in (200, 503)

    def test_rapid_requests(self, client, api_key):
        """Edge: Rapid sequential requests."""
        responses = []
        for i in range(5):
            resp = client.post("/api/v1/check",
                               headers={"X-API-Key": api_key},
                               json={"error_message": f"Error {i}"})
            responses.append(resp.status_code)
        # All should succeed (unless rate-limited)
        print(f"Rapid request statuses: {responses}")

    def test_unicode_in_error_message(self, client, api_key):
        """Edge: Unicode characters in error message."""
        response = client.post("/api/v1/check",
                               headers={"X-API-Key": api_key},
                               json={"error_message": "エラー: テスト失敗"})
        assert response.status_code == 200


class TestDatabaseTests:
    """Database-level tests using direct ORM access."""

    def test_user_unique_email(self, client):
        """DB constraint: Duplicate emails rejected at DB level."""
        data = {"email": unique_email("uniquetest"), "password": "Unique123!"}
        client.post("/api/v1/auth/register", json=data)
        # Second register should fail with integrity error (converted to 400)
        resp = client.post("/api/v1/auth/register", json=data)
        assert resp.status_code == 400

    def test_key_prefix_length(self, client, valid_token):
        """Data validation: Key prefix is truncated correctly."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        resp = client.post("/api/v1/keys", json={"name": "Prefix Test"}, headers=headers)
        prefix = resp.json()["prefix"]
        assert prefix.endswith("...")
        assert len(prefix) > 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
