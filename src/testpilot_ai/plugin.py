"""TestPilot AI - Core pytest plugin implementation."""

import pytest
import os
import json
from typing import Dict, List, Optional, Any
from pathlib import Path


def pytest_addoption(parser):
    """Add command-line options for TestPilot AI."""
    parser.addoption(
        "--testpilot",
        action="store_true",
        default=False,
        help="Enable TestPilot AI for intelligent test analysis",
    )
    parser.addoption(
        "--testpilot-scrub",
        action="store_true",
        default=False,
        help="Enable sensitive data scrubbing",
    )
    parser.addoption(
        "--testpilot-classify",
        action="store_true",
        default=False,
        help="Enable failure classification",
    )
    parser.addoption(
        "--testpilot-api-key",
        type=str,
        default=None,
        help="OpenAI API key for LLM features",
    )


def pytest_configure(config):
    """Configure TestPilot AI plugin."""
    if config.getoption("--testpilot"):
        config.testpilot_enabled = True
        
        # Initialize plugin state
        config.testpilot_state = {
            "failed_tests": [],
            "scrubbed_outputs": [],
            "classifications": {},
            "start_time": None,
        }
        
        # Set API key from option or environment
        api_key = config.getoption("--testpilot-api-key") or os.getenv("OPENAI_API_KEY")
        if api_key:
            config.testpilot_state["api_key"] = api_key


def pytest_unconfigure(config):
    """Cleanup TestPilot AI plugin."""
    if hasattr(config, 'testpilot_enabled') and config.testpilot_enabled:
        # Generate summary report
        _generate_summary_report(config)


def pytest_runtest_logreport(self, report):
    """Capture test results for analysis."""
    if not getattr(self.config, 'testpilot_enabled', False):
        return
    
    state = self.config.testpilot_state
    
    if report.when == "call" and report.failed:
        state["failed_tests"].append({
            "nodeid": report.nodeid,
            "longrepr": str(report.longrepr) if report.longrepr else "",
            "outcome": "failed",
            "duration": report.duration,
        })


def _generate_summary_report(config):
    """Generate a summary report of test results."""
    state = config.testpilot_state
    
    if not state["failed_tests"]:
        print("\n[TestPilot AI] No test failures detected.")
        return
    
    print(f"\n[TestPilot AI] Analysis complete:")
    print(f"  - Failed tests: {len(state['failed_tests'])}")
    print(f"  - Scrubbed outputs: {len(state['scrubbed_outputs'])}")
    print(f"  - Classifications: {len(state['classifications'])}")


# Register hook implementations
pytest_runtest_logreport = pytest_runtest_logreport  # noqa: F811
