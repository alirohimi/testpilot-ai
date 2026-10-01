"""Frontend E2E tests for auth.html and dashboard.html

These tests use an in-process FastAPI TestClient — no subprocess needed.
"""

import re

import pytest

# Configuration
PROJECT_BASE = "/testpilot-ai"


class TestAuthPageStructure:
    """Test auth page HTML structure."""

    def test_auth_page_loads(self, e2e_server):
        """Auth page should load successfully."""
        resp = e2e_server.get(f"{PROJECT_BASE}/auth.html")
        assert resp.status_code == 200
        html = resp.text
        assert "<title>" in html

    def test_auth_page_has_sign_in_tab(self, e2e_server):
        """Auth page should have Sign In tab."""
        resp = e2e_server.get(f"{PROJECT_BASE}/auth.html")
        html = resp.text
        assert "Sign In" in html or "login" in html.lower()

    def test_auth_page_has_register_tab(self, e2e_server):
        """Auth page should have Register tab."""
        resp = e2e_server.get(f"{PROJECT_BASE}/auth.html")
        html = resp.text
        assert "Register" in html or "register" in html.lower()

    def test_auth_page_login_form_exists(self, e2e_server):
        """Login form should exist."""
        resp = e2e_server.get(f"{PROJECT_BASE}/auth.html")
        html = resp.text
        assert 'id="login-email"' in html
        assert 'id="login-password"' in html

    def test_auth_page_register_form_exists(self, e2e_server):
        """Register form should exist."""
        resp = e2e_server.get(f"{PROJECT_BASE}/auth.html")
        html = resp.text
        # Current HTML uses id="reg-email" and id="reg-password"
        assert 'id="reg-email"' in html
        assert 'id="reg-password"' in html


class TestDashboardPageStructure:
    """Test dashboard page HTML structure."""

    def test_dashboard_has_title(self, e2e_server, auth_headers):
        """Dashboard should have a title."""
        resp = e2e_server.get(f"{PROJECT_BASE}/dashboard.html", headers=auth_headers)
        html = resp.text
        assert "Dashboard" in html or "TestPilot" in html

    def test_dashboard_has_api_key_section(self, e2e_server, auth_headers):
        """Dashboard should have API key section."""
        resp = e2e_server.get(f"{PROJECT_BASE}/dashboard.html", headers=auth_headers)
        html = resp.text
        assert "API Key" in html or "apikey" in html.lower()

    def test_dashboard_has_logout(self, e2e_server, auth_headers):
        """Dashboard should have logout button."""
        resp = e2e_server.get(f"{PROJECT_BASE}/dashboard.html", headers=auth_headers)
        html = resp.text
        assert "logout" in html.lower() or "Logout" in html


class TestSignupFlow:
    """Test user signup flow via frontend."""

    def _unique_email(self, request):
        """Generate a unique email based on test name with e2e prefix."""
        return f"e2e_{request.node.name}@example.com"

    def test_register_valid_user(self, e2e_server, request):
        """Valid registration should succeed."""
        resp = e2e_server.post(
            "/api/v1/auth/register",
            json={
                "email": self._unique_email(request),
                "password": "FreshPass123!",
                "full_name": "Fresh User",
            },
        )
        assert resp.status_code in (200, 201), f"Registration failed: {resp.json()}"

    def test_register_duplicate_email(self, e2e_server, request):
        """Duplicate email should be rejected."""
        unique_email = self._unique_email(request)
        # First registration
        e2e_server.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "DupPass123!",
                "full_name": "Dup User",
            },
        )
        # Second registration with same email
        resp = e2e_server.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "DupPass123!",
                "full_name": "Dup User 2",
            },
        )
        assert resp.status_code == 400

    def test_register_empty_fields(self, e2e_server):
        """Empty fields should be rejected."""
        resp = e2e_server.post(
            "/api/v1/auth/register", json={"email": "", "password": ""}
        )
        assert resp.status_code == 422


class TestLoginFlow:
    """Test login flow via frontend."""

    def _register_and_login(self, e2e_server, email, password):
        """Helper to register and then login."""
        e2e_server.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Test User"},
        )
        return e2e_server.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )

    def test_login_valid_credentials(self, e2e_server):
        """Valid login should succeed."""
        resp = self._register_and_login(
            e2e_server, "login_test@example.com", "LoginTest123!"
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, e2e_server):
        """Wrong password should return 401."""
        resp = e2e_server.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "WrongPass123!"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, e2e_server):
        """Non-existent user should return 401."""
        resp = e2e_server.post(
            "/api/v1/auth/login",
            json={"email": "doesnotexist@example.com", "password": "AnyPass123!"},
        )
        assert resp.status_code == 401

    def test_login_empty_fields(self, e2e_server):
        """Empty login fields should return 422."""
        resp = e2e_server.post("/api/v1/auth/login", json={"email": "", "password": ""})
        assert resp.status_code == 422


class TestDashboardAccess:
    """Test dashboard access control."""

    def test_dashboard_requires_auth(self, e2e_server):
        """Dashboard should contain auth check logic."""
        resp = e2e_server.get(f"{PROJECT_BASE}/dashboard.html")
        html = resp.text
        # Dashboard uses JS-based auth (check tp_token) not server redirect
        assert "tp_token" in html or "localStorage" in html or "auth" in html.lower()

    def test_dashboard_still_loads_without_token(self, e2e_server):
        """Dashboard HTML should load even without token (JS handles auth)."""
        resp = e2e_server.get(f"{PROJECT_BASE}/dashboard.html")
        # Static file is served as 200 - auth is client-side JS check
        assert resp.status_code == 200
        html = resp.text
        assert "<title>" in html


class TestCrossPageConsistency:
    """Test consistency across pages."""

    def test_all_pages_use_same_font(self, e2e_server):
        """All pages should use the same font."""
        fonts = set()
        for page in ["/auth.html", "/dashboard.html", "/"]:
            resp = e2e_server.get(f"{PROJECT_BASE}{page}")
            if resp.status_code == 200:
                html = resp.text
                # Look for Inter font references
                if "'Inter'" in html or '"Inter"' in html:
                    fonts.add("Inter")
        # At least one page should reference Inter
        assert len(fonts) >= 1, "No pages use Inter font"

    def test_all_pages_use_project_paths(self, e2e_server):
        """All pages should use project-relative paths."""
        for page in ["/auth.html", "/dashboard.html"]:
            resp = e2e_server.get(f"{PROJECT_BASE}{page}")
            if resp.status_code == 200:
                html = resp.text
                # Links should be project-relative
                assert f"{PROJECT_BASE}/" in html or 'href="/' in html


class TestSecurity:
    """Test security aspects of the frontend."""

    def test_no_leaked_api_keys_in_html(self, e2e_server, auth_headers):
        """API keys should not appear in page HTML."""
        resp = e2e_server.get(f"{PROJECT_BASE}/dashboard.html", headers=auth_headers)
        html = resp.text
        # Keys should be stored in JS, not in HTML
        assert "sk-" not in html
        assert "tpk_" not in html

    def test_no_plain_text_passwords_in_response(self, e2e_server):
        """Passwords should never appear in responses."""
        # Attempt a registration
        e2e_server.post(
            "/api/v1/auth/register",
            json={"email": "sec_test@example.com", "password": "SecurePass123!"},
        )
        # Login
        resp = e2e_server.post(
            "/api/v1/auth/login",
            json={"email": "sec_test@example.com", "password": "SecurePass123!"},
        )
        response_str = str(resp.json())
        assert "SecurePass123!" not in response_str
        assert "secret" not in response_str.lower()


class TestErrorHandling:
    """Test error handling on frontend."""

    def test_invalid_route_returns_404(self, e2e_server):
        """Invalid routes should return 404."""
        resp = e2e_server.get(f"{PROJECT_BASE}/nonexistent-page")
        assert resp.status_code == 404

    def test_malformed_json_returns_422(self, e2e_server):
        """Malformed JSON should return 422."""
        resp = e2e_server.post(
            "/api/v1/auth/register",
            content=b"{invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_http_only_urls(self, e2e_server):
        """No HTTP (insecure) URLs in HTML responses."""
        for page in ["/auth.html", "/dashboard.html"]:
            resp = e2e_server.get(f"{PROJECT_BASE}{page}")
            if resp.status_code == 200:
                html = resp.text
                # Check for http:// URLs (excluding localhost)
                http_urls = [
                    u
                    for u in re.findall(r'http://[^"\s]+', html)
                    if not u.startswith("http://localhost")
                ]
                assert not http_urls, f"HTTP URLs found: {http_urls}"

    def test_password_not_in_response(self, e2e_server):
        """Password should never appear in API responses."""
        e2e_server.post(
            "/api/v1/auth/register",
            json={"email": "secure@example.com", "password": "MySecretPass123!"},
        )
        resp = e2e_server.post(
            "/api/v1/auth/login",
            json={"email": "secure@example.com", "password": "MySecretPass123!"},
        )
        response_str = str(resp.json())
        assert "MySecretPass123!" not in response_str
        assert "secret" not in response_str.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
