#!/usr/bin/env python3
"""TestPilot AI - Frontend E2E Test Suite (Standalone Runner)

Runs comprehensive frontend tests without pytest dependency.
Tests deployed pages on GitHub Pages:
- Landing page structure and navigation
- Auth page forms and redirects
- Dashboard page functionality
- Cross-page consistency
- Security checks
"""

import re
import sys
import urllib.error
import urllib.request
from datetime import datetime

# Configuration
BASE_URL = "https://alirohimi.github.io/testpilot-ai"
TESTS = []
RESULTS = {"passed": 0, "failed": 0, "errors": 0}


class TestResult:
    def __init__(self, name, passed, message=""):
        self.name = name
        self.passed = passed
        self.message = message
        self.timestamp = datetime.now().isoformat()


def test(name, condition, message=""):
    """Run a single test."""
    result = TestResult(name, condition, message)
    TESTS.append(result)
    if condition:
        RESULTS["passed"] += 1
        print(f"  ✅ {name}")
    else:
        RESULTS["failed"] += 1
        print(f"  ❌ {name}: {message}")
    return result


def fetch_html(url):
    """Fetch HTML content from URL."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (TestPilot-E2E/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode("utf-8")
    except Exception:
        return None


def fetch_status(url):
    """Check HTTP status code."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Test"})
        response = urllib.request.urlopen(req, timeout=5)
        return response.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


# =====================
# 1. LANDING PAGE TESTS
# =====================


def test_landing_page():
    print("\n📄 Landing Page Tests")
    print("=" * 40)

    html = fetch_html(f"{BASE_URL}/")
    test("Landing page loads", html is not None, "Failed to fetch landing page")

    if not html:
        return

    test("Page has correct title", "<title>TestPilot AI" in html)
    test(
        "Logo links to project root",
        'href="/testpilot-ai/"' in html,
        "Logo should use /testpilot-ai/ not /",
    )
    test("No broken /ui/ paths", "/ui/" not in html)
    test("Has Features section", "Intelligent Classification" in html)
    test("Has How it Works section", "How it Works" in html)
    test("Has Pricing section", "Simple, per-seat pricing" in html)
    test("Has CTA buttons", "Get Started Free" in html and "See How It Works" in html)
    test("Has footer links", "GitHub" in html and "Documentation" in html)
    test("Has mobile menu button", "mobile-menu-btn" in html or "menu-toggle" in html)
    test("Has CSS variables", ":root" in html and "--bg:" in html)
    test("Uses Inter font", "'Inter'" in html or '"Inter"' in html)
    test("Has viewport meta", 'name="viewport"' in html)
    test("Preconnects to fonts", 'rel="preconnect"' in html)


# =====================
# 2. AUTH PAGE TESTS
# =====================


def test_auth_page():
    print("\n🔐 Auth Page Tests")
    print("=" * 40)

    html = fetch_html(f"{BASE_URL}/auth.html")
    test("Auth page loads", html is not None, "Failed to fetch auth page")

    if not html:
        return

    test("Page has correct title", "<title>TestPilot AI — Sign In</title>" in html)
    test("Has login panel", 'id="login-panel"' in html)
    test("Has register panel", 'id="register-panel"' in html)
    test("Has API key panel", 'id="key-panel"' in html)
    test("Login form has email field", 'id="login-email"' in html)
    test("Login form has password field", 'id="login-password"' in html)
    test("Register form has name field", 'id="reg-name"' in html)
    test(
        "Back to website links correct",
        'href="/testpilot-ai/"' in html,
        "Should use /testpilot-ai/ not /",
    )
    test(
        "No duplicate back links",
        html.count("Back to website") == 2,
        f"Expected 2 back links, found {html.count('Back to website')}",
    )
    test("Dashboard redirect uses project path", "/testpilot-ai/dashboard.html" in html)
    test("No /ui/ paths", "/ui/" not in html)
    test("API endpoint configured", "'/api/v1'" in html)
    test("Has token storage", "tp_token" in html)
    test("Has viewport meta", 'name="viewport"' in html)


# =====================
# 3. DASHBOARD PAGE TESTS
# =====================


def test_dashboard_page():
    print("\n📊 Dashboard Page Tests")
    print("=" * 40)

    html = fetch_html(f"{BASE_URL}/dashboard.html")
    test("Dashboard page loads", html is not None, "Failed to fetch dashboard page")

    if not html:
        return

    test("Page has correct title", "TestPilot AI" in html and "Dashboard" in html)
    test("Navigation links correct", 'href="/testpilot-ai/"' in html)
    test("Has API key management", "API Keys" in html)
    test("Has create key button", "Create" in html)
    test("Has delete functionality", "Delete" in html.lower() or "DELETE" in html)
    test("Has logout button", "logout" in html.lower())
    test("Checks for token", "tp_token" in html)
    test("No /ui/ paths", "/ui/" not in html)
    test("Has mobile menu", "mobile-menu-btn" in html or "sidebar-toggle" in html)
    test("Has viewport meta", 'name="viewport"' in html)


# =====================
# 4. CROSS-PAGE CONSISTENCY
# =====================


def test_cross_page_consistency():
    print("\n🔗 Cross-Page Consistency Tests")
    print("=" * 40)

    landing = fetch_html(f"{BASE_URL}/")
    auth = fetch_html(f"{BASE_URL}/auth.html")
    dashboard = fetch_html(f"{BASE_URL}/dashboard.html")

    if not all([landing, auth, dashboard]):
        test("All pages loaded", False, "Could not load all pages")
        return

    # CSS variable consistency
    landing_bg = re.search(r"--bg:\s*(#[0-9a-fA-F]{3,6})", landing)
    auth_bg = re.search(r"--bg:\s*(#[0-9a-fA-F]{3,6})", auth)
    dashboard_bg = re.search(r"--bg:\s*(#[0-9a-fA-F]{3,6})", dashboard)

    if landing_bg and auth_bg and dashboard_bg:
        test(
            "CSS --bg consistent",
            landing_bg.group(1) == auth_bg.group(1) == dashboard_bg.group(1),
        )

    # Font consistency
    test(
        "All use Inter font",
        "'Inter'" in landing and "'Inter'" in auth and "'Inter'" in dashboard,
    )

    # Branding consistency
    test("Auth has correct branding", "TestPilot AI" in auth)
    test("Dashboard has correct branding", "TestPilot AI" in dashboard)

    # All use project paths
    test("Auth uses project paths", 'href="/testpilot-ai/' in auth)
    test("Dashboard uses project paths", 'href="/testpilot-ai/' in dashboard)


# =====================
# 5. SECURITY TESTS
# =====================


def test_security():
    print("\n🔒 Security Tests")
    print("=" * 40)

    auth = fetch_html(f"{BASE_URL}/auth.html")
    dashboard = fetch_html(f"{BASE_URL}/dashboard.html")

    if not all([auth, dashboard]):
        test("Pages loaded for security check", False)
        return

    # No hardcoded credentials
    credential_patterns = [
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub token"),
        (r"sk-[a-zA-Z0-9]{20,}", "API key"),
    ]

    for pattern, desc in credential_patterns:
        found = re.findall(pattern, auth + dashboard)
        test(f"No hardcoded {desc}", not found)

    # HTTPS only
    http_urls = re.findall(r'http://[^\s"<>]+', auth + dashboard)
    real_http = [u for u in http_urls if not u.startswith("http://localhost")]
    test("No HTTP URLs (HTTPS only)", not real_http, f"Found: {real_http}")


# =====================
# 6. ERROR HANDLING
# =====================


def test_error_handling():
    print("\n🚨 Error Handling Tests")
    print("=" * 40)

    # 404 page exists
    status = fetch_status(f"{BASE_URL}/nonexistent-page-12345.html")
    test("404 returns proper error", status == 404, f"Got status {status}")

    # Auth page works without token
    auth = fetch_html(f"{BASE_URL}/auth.html")
    test("Auth shows login form", auth is not None and 'id="login-email"' in auth)

    # Dashboard redirects without token
    dashboard = fetch_html(f"{BASE_URL}/dashboard.html")
    test(
        "Dashboard checks for token", dashboard is not None and "tp_token" in dashboard
    )


# =====================
# MAIN
# =====================


def main():
    print("=" * 50)
    print("TestPilot AI - Frontend E2E Test Suite")
    print("=" * 50)

    test_landing_page()
    test_auth_page()
    test_dashboard_page()
    test_cross_page_consistency()
    test_security()
    test_error_handling()

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    total = RESULTS["passed"] + RESULTS["failed"] + RESULTS["errors"]
    print(f"Total: {total} tests")
    print(f"Passed: {RESULTS['passed']}")
    print(f"Failed: {RESULTS['failed']}")
    print(f"Errors: {RESULTS['errors']}")

    if RESULTS["failed"] > 0:
        print("\n❌ Some tests failed!")
        return 1
    else:
        print("\n✅ All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
