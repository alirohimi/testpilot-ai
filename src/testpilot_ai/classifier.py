"""TestPilot AI - Failure classification module."""

from typing import Dict, List, Optional, Tuple
from enum import Enum
import re


class FailureType(Enum):
    """Categories of test failures."""
    ASSERTION_ERROR = "assertion_error"
    VALUE_ERROR = "value_error"
    TYPE_ERROR = "type_error"
    IMPORT_ERROR = "import_error"
    TIMEOUT_ERROR = "timeout_error"
    PERMISSION_ERROR = "permission_error"
    CONNECTION_ERROR = "connection_error"
    KEY_ERROR = "key_error"
    INDEX_ERROR = "index_error"
    ATTRIBUTE_ERROR = "attribute_error"
    UNKNOWN = "unknown"


class TestPilotClassifier:
    """Classify test failures into categories."""
    
    CLASSIFICATION_PATTERNS = {
        FailureType.ASSERTION_ERROR: [
            r"AssertionError",
            r"assert\s",
            r"Expected.*but got",
            r"Assertion failed",
        ],
        FailureType.VALUE_ERROR: [
            r"ValueError",
            r"invalid literal for",
            r"invalid value",
        ],
        FailureType.TYPE_ERROR: [
            r"TypeError",
            r"expected.*got",
            r"unsupported operand type",
        ],
        FailureType.IMPORT_ERROR: [
            r"ImportError",
            r"ModuleNotFoundError",
            r"No module named",
        ],
        FailureType.TIMEOUT_ERROR: [
            r"TimeoutError",
            r"timed out",
            r"deadline exceeded",
        ],
        FailureType.PERMISSION_ERROR: [
            r"PermissionError",
            r"Permission denied",
            r"EACCES",
        ],
        FailureType.CONNECTION_ERROR: [
            r"ConnectionError",
            r"Connection refused",
            r"Cannot connect to host",
        ],
        FailureType.KEY_ERROR: [
            r"KeyError",
            r"key.*not found",
        ],
        FailureType.INDEX_ERROR: [
            r"IndexError",
            r"list index out of range",
            r"index.*out of range",
        ],
        FailureType.ATTRIBUTE_ERROR: [
            r"AttributeError",
            r"'NoneType' object has no attribute",
            r"has no attribute",
        ],
    }
    
    def __init__(self):
        self._compiled_patterns = {}
        for failure_type, patterns in self.CLASSIFICATION_PATTERNS.items():
            self._compiled_patterns[failure_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def classify(self, error_message: str) -> FailureType:
        """Classify an error message into a failure type."""
        for failure_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(error_message):
                    return failure_type
        return FailureType.UNKNOWN
    
    def classify_with_reason(self, error_message: str) -> Tuple[FailureType, str]:
        """Classify error and provide reasoning."""
        failure_type = self.classify(error_message)
        
        reasons = {
            FailureType.ASSERTION_ERROR: "Test assertion failed - expected value mismatch",
            FailureType.VALUE_ERROR: "Invalid value provided to function",
            FailureType.TYPE_ERROR: "Type mismatch in operation",
            FailureType.IMPORT_ERROR: "Missing module or package",
            FailureType.TIMEOUT_ERROR: "Operation timed out",
            FailureType.PERMISSION_ERROR: "Permission denied for operation",
            FailureType.CONNECTION_ERROR: "Network connection failed",
            FailureType.KEY_ERROR: "Dictionary key not found",
            FailureType.INDEX_ERROR: "Index out of range",
            FailureType.ATTRIBUTE_ERROR: "Attribute access on invalid object",
            FailureType.UNKNOWN: "Unable to classify - manual review needed",
        }
        
        return failure_type, reasons.get(failure_type, "Unknown failure type")
    
    def get_triage_suggestion(self, failure_type: FailureType) -> str:
        """Get suggested triage actions for a failure type."""
        suggestions = {
            FailureType.ASSERTION_ERROR: "Check test expectations and expected values",
            FailureType.VALUE_ERROR: "Validate input data and types",
            FailureType.TYPE_ERROR: "Check type annotations and conversions",
            FailureType.IMPORT_ERROR: "Verify dependencies are installed",
            FailureType.TIMEOUT_ERROR: "Increase timeout or optimize operation",
            FailureType.PERMISSION_ERROR: "Check file/directory permissions",
            FailureType.CONNECTION_ERROR: "Verify service availability and network",
            FailureType.KEY_ERROR: "Check dictionary structure and keys",
            FailureType.INDEX_ERROR: "Validate array/list bounds",
            FailureType.ATTRIBUTE_ERROR: "Check object initialization and types",
            FailureType.UNKNOWN: "Review error trace manually",
        }
        return suggestions.get(failure_type, "Manual review required")


# Module-level classifier instance
classifier = TestPilotClassifier()


def classify_failure(error_message: str) -> FailureType:
    """Convenience function to classify a failure."""
    return classifier.classify(error_message)


def get_triage_suggestion(failure_type: FailureType) -> str:
    """Convenience function to get triage suggestion."""
    return classifier.get_triage_suggestion(failure_type)
