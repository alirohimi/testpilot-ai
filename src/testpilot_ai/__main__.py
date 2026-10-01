"""TestPilot AI - Main package with public API."""

from .classifier import (
    FailureType,
    TestPilotClassifier,
    classify_failure,
    get_triage_suggestion,
)
from .llm import LLMConfig, TestPilotLLM, analyze_with_llm
from .plugin import (
    pytest_addoption,
    pytest_configure,
    pytest_runtest_logreport,
    pytest_unconfigure,
)
from .scrubber import Scrubber, scrub_result, scrub_text
from .triage import (
    TriageEngine,
    TriageRule,
    add_triage_rule,
    triage_failure,
)

__all__ = [
    # Plugin hooks
    "pytest_addoption",
    "pytest_configure",
    "pytest_unconfigure",
    "pytest_runtest_logreport",
    # Scrubber
    "Scrubber",
    "scrub_text",
    "scrub_result",
    # Classifier
    "TestPilotClassifier",
    "FailureType",
    "classify_failure",
    "get_triage_suggestion",
    # LLM
    "TestPilotLLM",
    "LLMConfig",
    "analyze_with_llm",
    # Triage
    "TriageEngine",
    "TriageRule",
    "triage_failure",
    "add_triage_rule",
]

__version__ = "0.1.0"
