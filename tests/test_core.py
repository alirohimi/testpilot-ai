"""Tests for TestPilot AI plugin."""

import pytest

from testpilot_ai.classifier import FailureType, TestPilotClassifier
from testpilot_ai.scrubber import Scrubber
from testpilot_ai.triage import triage_failure


class TestScrubber:
    """Tests for the Scrubber class."""

    def test_scrub_email(self):
        """Test email scrubbing."""
        scrubber = Scrubber()
        text = "Contact us at test@example.com for help"
        result = scrubber.scrub(text)
        assert "test@example.com" not in result
        assert "[email_redacted]" in result

    def test_scrub_api_key(self):
        """Test API key scrubbing."""
        scrubber = Scrubber()
        text = "Using token ghp_abc123def456ghi789jkl012mno345pqr678"
        result = scrubber.scrub(text)
        assert "ghp_" not in result
        assert "[api_key_redacted]" in result

    def test_scrub_disabled(self):
        """Test scrubbing when disabled."""
        scrubber = Scrubber(enabled=False)
        text = "Contact: secret@email.com"
        result = scrubber.scrub(text)
        assert result == text

    def test_scrub_dict(self):
        """Test dict scrubbing."""
        scrubber = Scrubber()
        data = {
            "email": "user@example.com",
            "nested": {"password": "password: secret123"},
        }
        result = scrubber.scrub_dict(data)
        assert "user@example.com" not in result["email"]
        assert "secret123" not in result["nested"]["password"]


class TestClassifier:
    """Tests for the Classifier class."""

    def test_classify_assertion_error(self):
        """Test assertion error classification."""
        classifier = TestPilotClassifier()
        error = "AssertionError: Expected 5 but got 3"
        result = classifier.classify(error)
        assert result == FailureType.ASSERTION_ERROR

    def test_classify_import_error(self):
        """Test import error classification."""
        classifier = TestPilotClassifier()
        error = "ModuleNotFoundError: No module named 'nonexistent'"
        result = classifier.classify(error)
        assert result == FailureType.IMPORT_ERROR

    def test_classify_unknown(self):
        """Test unknown error classification."""
        classifier = TestPilotClassifier()
        error = "Some unusual error occurred"
        result = classifier.classify(error)
        assert result == FailureType.UNKNOWN

    def test_get_suggestion(self):
        """Test triage suggestion retrieval."""
        classifier = TestPilotClassifier()
        suggestion = classifier.get_triage_suggestion(FailureType.TIMEOUT_ERROR)
        assert "timeout" in suggestion.lower()


class TestTriage:
    """Tests for the Triage engine."""

    def test_trage_missing_dependency(self):
        """Test triage for missing dependency."""
        error = "ModuleNotFoundError: No module named 'requests'"
        result = triage_failure(error)
        assert result["category"] == "infrastructure"
        assert result["severity"] in ["critical", "high"]

    def test_trage_assertion(self):
        """Test triage for assertion failure."""
        error = "AssertionError: assert x == y"
        result = triage_failure(error)
        assert result["category"] == "test_logic"

    def test_trage_permission(self):
        """Test triage for permission error."""
        error = "PermissionError: [Errno 13] Permission denied"
        result = triage_failure(error)
        assert result["severity"] == "critical"


class TestPlugin:
    """Tests for pytest plugin integration."""

    def test_plugin_loads(self, pytestconfig):
        """Test that plugin loads correctly."""
        # This is a placeholder - actual integration tests would run pytest
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
