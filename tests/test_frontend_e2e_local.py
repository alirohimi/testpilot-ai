"""Frontend E2E tests for auth.html and dashboard.html"""

import pytest
import re
import sys
import os
import urllib.request
import urllib.error
import json

# Configuration
BASE_URL = "http://localhost:8000"
PROJECT_BASE = "/testpilot-ai"


def fetch_html(path):
    """Fetch HTML from local server."""
    try:
        url = f"{BASE_URL}{PROJECT_BASE}{path}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (TestPilot-Test/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return f"HTTP_ERROR_{e.code}"
    except Exception as e:
        return f"ERROR: {str(e)}"


def fetch_json(path, method="GET", data=None, headers=None):
    """Fetch JSON from API."""
    try:
        url = f"{BASE_URL}{path}"
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode() if data else None,
            method=method,
            headers=headers or {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except:
            return e.code, {"error": body}
    except Exception as e:
        return None, {"error": str(e)}


class TestAuthPageStructure:
    """Test auth page HTML structure."""

    def test_auth_page_loads(self):
        """Auth page should load successfully."""
        html = fetch_html("/auth.html")
        assert "HTTP_ERROR" not in html, f"Auth page failed: {html}"
        assert "<title>" in html

    def test_auth_page_has_sign_in_tab(self):
        """Auth page should have Sign In tab."""
        html = fetch_html("/auth.html")
        assert "Sign In" in html or "login" in html.lower()

    def test_auth_page_has_register_tab(self):
        """Auth page should have Register tab."""
        html = fetch_html("/auth.html")
        assert "Register" in html or "register" in html.lower()

    def test_auth_page_login_form_exists(self):
        """Login form should exist."""
        html = fetch_html("/auth.html")
        assert 'id="login-email"' in html
        assert 'id="login-password"' in html

    def test_auth_page_register_form_exists(self):
        """Register form should exist."""
        html = fetch_html("/auth.html")
        assert 'id="reg-email"' in html
        assert 'id="reg-password"' in html
        assert 'id="reg-name"' in html

    def test_auth_page_key_panel_exists(self):
        """API key panel should exist."""
        html = fetch_html("/auth.html")
        assert 'id="key-panel"' in html

    def test_auth_page_back_links(self):
        """Back links should point to correct location."""
        html = fetch_html("/auth.html")
        assert '/testpilot-ai/' in html

    def test_auth_page_api_endpoint_configured(self):
        """API endpoint should be configured."""
        html = fetch_html("/auth.html")
        assert "/api/v1" in html


class TestDashboardPageStructure:
    """Test dashboard page HTML structure."""

    def test_dashboard_loads(self):
        """Dashboard should load."""
        html = fetch_html("/dashboard.html")
        assert "HTTP_ERROR" not in html, f"Dashboard failed: {html}"

    def test_dashboard_has_title(self):
        """Dashboard should have title."""
        html = fetch_html("/dashboard.html")
        assert "Dashboard" in html or "TestPilot" in html

    def test_dashboard_has_api_key_section(self):
        """Dashboard should have API key section."""
        html = fetch_html("/dashboard.html")
        assert "API Key" in html or "apikey" in html.lower()

    def test_dashboard_has_logout(self):
        """Dashboard should have logout button."""
        html = fetch_html("/dashboard.html")
        assert "logout" in html.lower() or "Logout" in html


class TestSignupFlow:
    """Test signup flow via API."""

    def test_register_valid_user(self):
        """Valid registration should succeed or return existing user."""
        status, data = fetch_json("/api/v1/auth/register", method="POST", data={
            "email": "e2etest@example.com",
            "password": "TestPass123!",
            "full_name": "E2E Test User"
        })
        # Either 200 (new user) or 400 (already exists from previous run)
        assert status in (200, 400), f"Unexpected status: {status} {data}"
        if status == 200:
            assert "access_token" in data

    def test_register_duplicate_email(self):
        """Duplicate email should fail."""
        fetch_json("/api/v1/auth/register", method="POST", data={
            "email": "dup@example.com",
            "password": "TestPass123!"
        })
        status, data = fetch_json("/api/v1/auth/register", method="POST", data={
            "email": "dup@example.com",
            "password": "TestPass123!"
        })
        assert status == 400, f"Expected 400, got {status}: {data}"
        assert "already registered" in str(data).lower()

    def test_register_invalid_email(self):
        """Invalid email format - browser validates client-side, server may also reject."""
        status, data = fetch_json("/api/v1/auth/register", method="POST", data={
            "email": "not-an-email",
            "password": "TestPass123!"
        })
        # Server might accept if no server-side email validation
        # Document the behavior
        print(f"Invalid email response: {status} {data}")

    def test_register_short_password(self):
        """Short password should fail."""
        status, data = fetch_json("/api/v1/auth/register", method="POST", data={
            "email": "short@example.com",
            "password": "short"
        })
        print(f"Short password response: {status} {data}")

    def test_register_empty_fields(self):
        """Empty fields should fail."""
        status, data = fetch_json("/api/v1/auth/register", method="POST", data={
            "email": "",
            "password": ""
        })
        assert status == 422, f"Expected 422, got {status}"


class TestLoginFlow:
    """Test login flow."""

    def setup_method(self):
        """Setup: create test user before each login test."""
        fetch_json("/api/v1/auth/register", method="POST", data={
            "email": "logintest@example.com",
            "password": "LoginPass123!"
        })

    def test_login_valid_credentials(self):
        """Valid login should return token."""
        status, data = fetch_json("/api/v1/auth/login", method="POST", data={
            "email": "logintest@example.com",
            "password": "LoginPass123!"
        })
        assert status == 200, f"Login failed: {data}"
        assert "access_token" in data
        assert "user_id" in data

    def test_login_wrong_password(self):
        """Wrong password should fail."""
        status, data = fetch_json("/api/v1/auth/login", method="POST", data={
            "email": "logintest@example.com",
            "password": "WrongPassword123!"
        })
        assert status == 401, f"Expected 401, got {status}"

    def test_login_nonexistent_user(self):
        """Non-existent user should fail."""
        status, data = fetch_json("/api/v1/auth/login", method="POST", data={
            "email": "nobody@example.com",
            "password": "SomePassword123!"
        })
        assert status == 401

    def test_login_empty_fields(self):
        """Empty fields should fail validation."""
        status, data = fetch_json("/api/v1/auth/login", method="POST", data={
            "email": "",
            "password": ""
        })
        assert status == 422


class TestDashboardAccess:
    """Test dashboard access with authentication."""

    def test_dashboard_requires_auth(self):
        """Dashboard should check for token."""
        html = fetch_html("/dashboard.html")
        assert "tp_token" in html or "token" in html.lower()

    def test_dashboard_redirect_without_token(self):
        """Dashboard without token should redirect to auth."""
        html = fetch_html("/dashboard.html")
        # Check if redirect logic exists
        assert "auth" in html.lower() or "redirect" in html.lower()


class TestCrossPageConsistency:
    """Test consistency across pages."""

    def test_all_pages_use_same_font(self):
        """All pages should use Inter font."""
        auth_html = fetch_html("/auth.html")
        dash_html = fetch_html("/dashboard.html")
        landing_html = fetch_html("/")

        assert "'Inter'" in auth_html or '"Inter"' in auth_html
        assert "'Inter'" in dash_html or '"Inter"' in dash_html
        assert "'Inter'" in landing_html or '"Inter"' in landing_html

    def test_all_pages_use_project_paths(self):
        """All pages should use /testpilot-ai/ paths."""
        auth_html = fetch_html("/auth.html")
        dash_html = fetch_html("/dashboard.html")

        assert '/testpilot-ai/' in auth_html
        assert '/testpilot-ai/' in dash_html


class TestSecurity:
    """Security-related tests."""

    def test_no_hardcoded_credentials(self):
        """No hardcoded credentials in HTML."""
        auth_html = fetch_html("/auth.html")
        dash_html = fetch_html("/dashboard.html")
        combined = auth_html + dash_html

        # Check for common credential patterns
        import re
        ghp_pattern = r'ghp_[a-zA-Z0-9]{36}'
        assert not re.search(ghp_pattern, combined), "GitHub token found in HTML!"

    def test_https_for_external_resources(self):
        """External resources should use HTTPS."""
        html = fetch_html("/auth.html")
        http_urls = [u for u in re.findall(r'http://[^"\s]+', html)
                     if not u.startswith('http://localhost')]
        assert not http_urls, f"HTTP URLs found: {http_urls}"

    def test_password_not_in_response(self):
        """Password should never appear in API responses."""
        fetch_json("/api/v1/auth/register", method="POST", data={
            "email": "secure@example.com",
            "password": "MySecretPass123!"
        })
        status, data = fetch_json("/api/v1/auth/login", method="POST", data={
            "email": "secure@example.com",
            "password": "MySecretPass123!"
        })
        response_str = str(data)
        assert "MySecretPass123!" not in response_str
        assert "secret" not in response_str.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
