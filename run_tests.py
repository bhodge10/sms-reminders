#!/usr/bin/env python
"""
Test Runner for Remyndrs SMS Service

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --quick            # Run only quick unit tests
    python run_tests.py --scenarios        # Run only full scenario tests
    python run_tests.py --onboarding       # Run only onboarding tests
    python run_tests.py --reminders        # Run only reminder tests
    python run_tests.py --lists            # Run only list tests
    python run_tests.py --memories         # Run only memory tests
    python run_tests.py --edge             # Run only edge case tests
    python run_tests.py --tasks            # Run only background task tests
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --verbose          # Extra verbose output
    python run_tests.py --collect          # Just list tests without running

First, install dependencies:
    pip install -r requirements.txt
"""

import sys
import subprocess
import argparse


def check_dependencies():
    """Check that required packages are installed."""
    missing = []
    required = ['pytest', 'pytest_asyncio', 'pytz', 'fastapi', 'twilio', 'openai']
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            missing.append(pkg)

    if missing:
        print("ERROR: Missing required packages:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nPlease run: pip install -r requirements.txt")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Run Remyndrs test suite")
    parser.add_argument("--quick", action="store_true", help="Run only quick unit tests (skip slow tests)")
    parser.add_argument("--scenarios", action="store_true", help="Run only full scenario tests")
    parser.add_argument("--onboarding", action="store_true", help="Run only onboarding tests")
    parser.add_argument("--reminders", action="store_true", help="Run only reminder tests")
    parser.add_argument("--lists", action="store_true", help="Run only list tests")
    parser.add_argument("--memories", action="store_true", help="Run only memory tests")
    parser.add_argument("--edge", action="store_true", help="Run only edge case tests")
    parser.add_argument("--tasks", action="store_true", help="Run only background task tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Extra verbose output")
    parser.add_argument("--failed", action="store_true", help="Re-run only failed tests from last run")
    parser.add_argument("--collect", action="store_true", help="Just list tests without running")
    parser.add_argument("--no-check", action="store_true", help="Skip dependency check")

    args = parser.parse_args()

    # Check dependencies unless skipped
    if not args.no_check:
        check_dependencies()

    # Build pytest command
    cmd = ["python", "-m", "pytest"]

    # Add verbosity
    if args.verbose:
        cmd.extend(["-vvv", "--tb=long"])
    else:
        cmd.extend(["-v", "--tb=short"])

    # Add coverage
    if args.coverage:
        cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term-missing"])

    # Add re-run failed
    if args.failed:
        cmd.append("--lf")

    # Just collect/list tests
    if args.collect:
        cmd.append("--collect-only")

    # Select specific test files
    if args.quick:
        cmd.extend(["-m", "not slow"])
    elif args.scenarios:
        cmd.append("tests/test_scenarios.py")
    elif args.onboarding:
        cmd.append("tests/test_onboarding.py")
    elif args.reminders:
        cmd.append("tests/test_reminders.py")
    elif args.lists:
        cmd.append("tests/test_lists.py")
    elif args.memories:
        cmd.append("tests/test_memories.py")
    elif args.edge:
        cmd.append("tests/test_edge_cases.py")
    elif args.tasks:
        cmd.append("tests/test_background_tasks.py")

    # Run pytest
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
