#!/usr/bin/env python3
"""Test runner script for TestPilot AI test suite."""

import subprocess
import sys
import os


def run_tests(test_path=None, verbose=False, cov=False):
    """Run pytest tests."""
    cmd = [sys.executable, "-m", "pytest"]

    if verbose:
        cmd.append("-v")
    if cov:
        cmd.extend(["--cov=api", "--cov-report=term-missing"])

    if test_path:
        cmd.append(test_path)
    else:
        cmd.append("tests/")

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--verbose":
            return run_tests(verbose=True)
        elif sys.argv[1] == "--cov":
            return run_tests(cov=True)
        elif sys.argv[1] == "--auth":
            return run_tests("tests/test_api_auth.py")
        elif sys.argv[1] == "--login":
            return run_tests("tests/test_api_login.py")
        elif sys.argv[1] == "--crud":
            return run_tests("tests/test_api_crud.py")
        elif sys.argv[1] == "--integration":
            return run_tests("tests/test_api_integration.py")
        elif sys.argv[1] == "--frontend":
            return run_tests("tests/test_frontend_e2e_local.py")
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python run_tests.py [--verbose] [--cov] [--auth|--login|--crud|--integration|--frontend]")
            return 1
    else:
        return run_tests()


if __name__ == "__main__":
    sys.exit(main())
