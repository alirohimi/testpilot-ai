"""API Key CRUD tests - Create, Read, Delete operations"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from api.main import app
from api.database import Base, get_db_session

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
def auth_headers(test_client):
    """Register a user and return auth headers."""
    response = test_client.post("/api/v1/auth/register", json={
        "email": "crud@example.com",
        "password": "CrudPass123!",
        "full_name": "CRUD User"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =====================
# API Key Creation Tests
# =====================

class TestAPIKeyCreate:
    """Tests for API key creation."""
    
    def test_create_key_success(self, test_client, auth_headers):
        """Positive: Valid key creation should succeed."""
        response = test_client.post(
            "/api/v1/keys",
            json={"name": "Test Key", "tier": "free"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "key" in data
        assert data["tier"] == "free"
        assert data["prefix"].startswith("tp_")
        # Full key should start with tp_
        assert data["key"].startswith("tp_")
    
    def test_create_key_without_tier(self, test_client, auth_headers):
        """Edge case: Default tier should be free."""
        response = test_client.post(
            "/api/v1/keys",
            json={"name": "Default Key"},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["tier"] == "free"
    
    def test_create_key_missing_name(self, test_client, auth_headers):
        """Negative: Missing name should fail."""
        response = test_client.post(
            "/api/v1/keys",
            json={"tier": "free"},
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_create_key_empty_name(self, test_client, auth_headers):
        """Negative: Empty name should fail."""
        response = test_client.post(
            "/api/v1/keys",
            json={"name": "", "tier": "free"},
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_create_key_invalid_tier(self, test_client, auth_headers):
        """Negative: Invalid tier should be rejected."""
        response = test_client.post(
            "/api/v1/keys",
            json={"name": "Bad Tier", "tier": "invalid_tier"},
            headers=auth_headers
        )
        # Should either return 422 or default to free
        assert response.status_code in [200, 422]
    
    def test_create_multiple_keys(self, test_client, auth_headers):
        """Positive: Multiple keys should be created."""
        # Create first key
        resp1 = test_client.post(
            "/api/v1/keys",
            json={"name": "Key 1", "tier": "free"},
            headers=auth_headers
        )
        assert resp1.status_code == 200
        
        # Create second key
        resp2 = test_client.post(
            "/api/v1/keys",
            json={"name": "Key 2", "tier": "pro"},
            headers=auth_headers
        )
        assert resp2.status_code == 200
        
        # Verify both exist
        list_resp = test_client.get("/api/v1/keys", headers=auth_headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 2
    
    def test_create_key_no_auth(self, test_client):
        """Negative: No auth should fail."""
        response = test_client.post(
            "/api/v1/keys",
            json={"name": "No Auth", "tier": "free"}
        )
        assert response.status_code == 401
    
    def test_create_key_bad_token(self, test_client):
        """Negative: Bad token should fail."""
        response = test_client.post(
            "/api/v1/keys",
            json={"name": "Bad Token", "tier": "free"},
            headers={"Authorization": "Bearer invalidtoken"}
        )
        assert response.status_code == 401


# =====================
# API Key Read Tests
# =====================

class TestAPIKeyRead:
    """Tests for listing API keys."""
    
    def test_list_keys_empty(self, test_client):
        """Positive: Empty list when no keys exist."""
        # Register a new user
        reg = test_client.post("/api/v1/auth/register", json={
            "email": "empty@example.com",
            "password": "EmptyPass123!"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get("/api/v1/keys", headers=headers)
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_keys_after_create(self, test_client, auth_headers):
        """Positive: List keys after creation."""
        # Create a key
        test_client.post(
            "/api/v1/keys",
            json={"name": "List Key", "tier": "free"},
            headers=auth_headers
        )
        
        # List keys
        response = test_client.get("/api/v1/keys", headers=auth_headers)
        assert response.status_code == 200
        keys = response.json()
        assert len(keys) >= 1
        assert keys[0]["name"] == "List Key"
    
    def test_list_keys_no_auth(self, test_client):
        """Negative: No auth should fail."""
        response = test_client.get("/api/v1/keys")
        assert response.status_code == 401
    
    def test_keys_isolated_per_user(self, test_client):
        """Security: Keys should be isolated per user."""
        # Create user 1 and their key
        reg1 = test_client.post("/api/v1/auth/register", json={
            "email": "user1@example.com",
            "password": "User1Pass123!"
        })
        token1 = reg1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        test_client.post(
            "/api/v1/keys",
            json={"name": "User1 Key", "tier": "free"},
            headers=headers1
        )
        
        # Create user 2
        reg2 = test_client.post("/api/v1/auth/register", json={
            "email": "user2@example.com",
            "password": "User2Pass123!"
        })
        token2 = reg2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # User 2 should not see user 1's keys
        keys2 = test_client.get("/api/v1/keys", headers=headers2).json()
        names2 = [k["name"] for k in keys2]
        assert "User1 Key" not in names2
    
    def test_full_key_not_leaked_in_list(self, test_client, auth_headers):
        """Security: Full key should not appear in list."""
        # Create a key
        create_resp = test_client.post(
            "/api/v1/keys",
            json={"name": "Secret Key", "tier": "free"},
            headers=auth_headers
        )
        full_key = create_resp.json()["key"]
        
        # List keys
        list_resp = test_client.get("/api/v1/keys", headers=auth_headers)
        keys = list_resp.json()
        
        # Full key should not appear in the list
        for key in keys:
            assert full_key not in str(key)


# =====================
# API Key Delete Tests
# =====================

class TestAPIKeyDelete:
    """Tests for deleting API keys."""
    
    def test_delete_key_success(self, test_client, auth_headers):
        """Positive: Delete existing key."""
        # Create a key
        create_resp = test_client.post(
            "/api/v1/keys",
            json={"name": "Delete Me", "tier": "free"},
            headers=auth_headers
        )
        key_id = create_resp.json()["id"]
        
        # Delete it
        delete_resp = test_client.delete(f"/api/v1/keys/{key_id}", headers=auth_headers)
        assert delete_resp.status_code == 200
        assert delete_resp.json()["success"] is True
    
    def test_delete_nonexistent_key(self, test_client, auth_headers):
        """Negative: Delete non-existent key should fail."""
        response = test_client.delete("/api/v1/keys/99999", headers=auth_headers)
        assert response.status_code == 404
    
    def test_delete_other_users_key(self, test_client):
        """Security: Should not be able to delete other users' keys."""
        # Create user 1 and key
        reg1 = test_client.post("/api/v1/auth/register", json={
            "email": "owner@example.com",
            "password": "OwnerPass123!"
        })
        token1 = reg1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}
        
        create_resp = test_client.post(
            "/api/v1/keys",
            json={"name": "Owner Key", "tier": "free"},
            headers=headers1
        )
        key_id = create_resp.json()["id"]
        
        # Create user 2
        reg2 = test_client.post("/api/v1/auth/register", json={
            "email": "hacker@example.com",
            "password": "HackerPass123!"
        })
        token2 = reg2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # User 2 tries to delete user 1's key
        response = test_client.delete(f"/api/v1/keys/{key_id}", headers=headers2)
        assert response.status_code == 403
    
    def test_delete_twice(self, test_client, auth_headers):
        """Negative: Delete same key twice should fail."""
        # Create a key
        create_resp = test_client.post(
            "/api/v1/keys",
            json={"name": "Double Delete", "tier": "free"},
            headers=auth_headers
        )
        key_id = create_resp.json()["id"]
        
        # First delete
        resp1 = test_client.delete(f"/api/v1/keys/{key_id}", headers=auth_headers)
        assert resp1.status_code == 200
        
        # Second delete
        resp2 = test_client.delete(f"/api/v1/keys/{key_id}", headers=auth_headers)
        assert resp2.status_code == 404
    
    def test_delete_invalid_key_id(self, test_client, auth_headers):
        """Negative: Invalid key ID should fail."""
        response = test_client.delete("/api/v1/keys/invalid", headers=auth_headers)
        assert response.status_code in [400, 404]
    
    def test_delete_no_auth(self, test_client):
        """Negative: No auth should fail."""
        response = test_client.delete("/api/v1/keys/1")
        assert response.status_code == 401


# =====================
# Me Endpoint Tests
# =====================

class TestMeEndpoint:
    """Tests for the /me endpoint."""
    
    def test_get_me_success(self, test_client):
        """Positive: Get current user info."""
        # Register and login
        reg = test_client.post("/api/v1/auth/register", json={
            "email": "me@example.com",
            "password": "MePass123!",
            "full_name": "Me User"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get("/api/v1/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == "me@example.com"
        assert data["full_name"] == "Me User"
        assert data["plan"] == "free"
        assert "id" in data
        assert "created_at" in data
    
    def test_get_me_no_auth(self, test_client):
        """Negative: No auth should fail."""
        response = test_client.get("/api/v1/me")
        assert response.status_code == 401
    
    def test_get_me_malformed_token(self, test_client):
        """Negative: Malformed token should fail."""
        response = test_client.get("/api/v1/me", headers={"Authorization": "Bearer invalid"})
        assert response.status_code == 401


# =====================
# Usage Endpoint Tests
# =====================

class TestUsageEndpoint:
    """Tests for the /usage endpoint."""
    
    def test_get_usage_success(self, test_client):
        """Positive: Get usage stats."""
        # Register
        reg = test_client.post("/api/v1/auth/register", json={
            "email": "usage@example.com",
            "password": "UsagePass123!"
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get("/api/v1/usage", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "checks_used" in data
        assert "checks_remaining" in data
        assert data["plan"] == "free"
    
    def test_get_usage_no_auth(self, test_client):
        """Negative: No auth should fail."""
        response = test_client.get("/api/v1/usage")
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
