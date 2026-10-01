"""TestPilot AI - Triage rules for test failures."""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class TriageRule:
    """A rule for triaging test failures."""

    name: str
    pattern: str
    severity: str
    category: str
    description: str
    suggested_fix: str
    priority: int = 100


class TriageEngine:
    """Engine for triaging test failures using rules."""

    def __init__(self):
        self.rules: list[TriageRule] = []
        self._compiled_rules: list[tuple[TriageRule, re.Pattern]] = []
        self._load_builtin_rules()

    def _load_builtin_rules(self):
        """Load builtin triage rules."""
        builtin_rules = [
            TriageRule(
                name="missing-dependency",
                pattern=r"ModuleNotFoundError|ImportError|No module named",
                severity="high",
                category="infrastructure",
                description="Test failed due to missing dependency",
                suggested_fix="Install required package: pip install <package-name>",
                priority=10,
            ),
            TriageRule(
                name="assertion-failure",
                pattern=r"AssertionError|assert\s",
                severity="medium",
                category="test_logic",
                description="Test assertion failed",
                suggested_fix="Review test expectations and actual values",
                priority=20,
            ),
            TriageRule(
                name="timeout",
                pattern=r"TimeoutError|timed out|deadline exceeded",
                severity="high",
                category="performance",
                description="Test timed out",
                suggested_fix="Increase timeout or optimize slow operation",
                priority=15,
            ),
            TriageRule(
                name="permission-denied",
                pattern=r"PermissionError|Permission denied|EACCES",
                severity="critical",
                category="infrastructure",
                description="Permission denied for file operation",
                suggested_fix="Check file permissions and running user",
                priority=5,
            ),
            TriageRule(
                name="connection-error",
                pattern=r"ConnectionError|Connection refused|Cannot connect",
                severity="critical",
                category="infrastructure",
                description="Network connection failed",
                suggested_fix="Verify service is running and network is available",
                priority=5,
            ),
            TriageRule(
                name="type-error",
                pattern=r"TypeError|expected.*got",
                severity="medium",
                category="code_quality",
                description="Type mismatch in operation",
                suggested_fix="Check type annotations and conversions",
                priority=30,
            ),
            TriageRule(
                name="value-error",
                pattern=r"ValueError|invalid literal",
                severity="low",
                category="test_data",
                description="Invalid value provided",
                suggested_fix="Validate input data and expected values",
                priority=40,
            ),
            TriageRule(
                name="key-error",
                pattern=r"KeyError|key.*not found",
                severity="medium",
                category="test_data",
                description="Dictionary key not found",
                suggested_fix="Check dictionary structure and expected keys",
                priority=30,
            ),
            TriageRule(
                name="index-error",
                pattern=r"IndexError|index.*out of range",
                severity="low",
                category="test_data",
                description="Index out of range",
                suggested_fix="Validate array/list bounds",
                priority=40,
            ),
            TriageRule(
                name="attribute-error",
                pattern=r"AttributeError|has no attribute",
                severity="medium",
                category="code_quality",
                description="Attribute access on invalid object",
                suggested_fix="Check object initialization and types",
                priority=30,
            ),
        ]

        for rule in builtin_rules:
            self.add_rule(rule)

    def add_rule(self, rule: TriageRule):
        """Add a triage rule."""
        rule.pattern = re.compile(rule.pattern, re.IGNORECASE)
        self.rules.append(rule)
        self._compiled_rules.append((rule, rule.pattern))
        # Sort by priority
        self._compiled_rules.sort(key=lambda x: x[0].priority)

    def triage(self, error_message: str) -> dict[str, Any]:
        """Triage an error message against all rules."""
        matches = []

        for rule, pattern in self._compiled_rules:
            if pattern.search(error_message):
                matches.append(
                    {
                        "rule": rule.name,
                        "severity": rule.severity,
                        "category": rule.category,
                        "description": rule.description,
                        "suggested_fix": rule.suggested_fix,
                    }
                )

        # Return best match (highest priority = lowest number)
        if matches:
            return matches[0]

        return {
            "rule": "unknown",
            "severity": "medium",
            "category": "unknown",
            "description": "Unable to classify failure automatically",
            "suggested_fix": "Manual review required",
        }

    def triage_all(self, failures: list[dict[str, str]]) -> list[dict[str, Any]]:
        """Triage multiple failures."""
        return [self.triage(f.get("error", "")) for f in failures]


# Module-level engine
triage_engine = TriageEngine()


def triage_failure(error_message: str) -> dict[str, Any]:
    """Convenience function to triage a failure."""
    return triage_engine.triage(error_message)


def add_triage_rule(rule: TriageRule):
    """Add a custom triage rule."""
    triage_engine.add_rule(rule)
