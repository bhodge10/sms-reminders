#!/usr/bin/env python3
"""
SMS Reminders Test Runner
Comprehensive test execution script with multiple modes.

Usage:
    # Run all tests
    python tests/run_tests.py

    # Run specific test suite
    python tests/run_tests.py --suite unit
    python tests/run_tests.py --suite integration
    python tests/run_tests.py --suite journeys
    python tests/run_tests.py --suite stress

    # Run stress simulation
    python tests/run_tests.py --stress --users 50 --messages 100

    # Quick smoke test
    python tests/run_tests.py --smoke

    # Generate HTML report
    python tests/run_tests.py --html-report
"""

import os
import sys
import argparse
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_pytest(test_path: str, extra_args: list = None, verbose: bool = True) -> int:
    """Run pytest on specified path"""
    cmd = ['python', '-m', 'pytest', test_path]

    if verbose:
        cmd.append('-v')

    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd)
    return result.returncode


def run_unit_tests() -> int:
    """Run unit tests (test_commands.py)"""
    return run_pytest('tests/test_commands.py', ['-k', 'not integration'])


def run_integration_tests() -> int:
    """Run integration tests"""
    return run_pytest('tests/test_commands.py', ['-m', 'integration'])


def run_journey_tests() -> int:
    """Run user journey tests"""
    return run_pytest('tests/test_user_journeys.py')


def run_stress_tests(users: int = 10, messages: int = 20, workers: int = 5) -> int:
    """Run stress simulation"""
    cmd = [
        'python', 'tests/stress_test.py',
        '--simulate',
        '--users', str(users),
        '--messages', str(messages),
        '--workers', str(workers),
        '--output', f'tests/stress_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    ]

    print(f"\n{'='*60}")
    print(f"Running Stress Test: {users} users, {messages} messages each")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd)
    return result.returncode


def run_smoke_tests() -> int:
    """Run quick smoke tests to verify basic functionality"""
    # Just run a subset of critical tests
    return run_pytest('tests/', [
        '-k', 'test_complete_onboarding or test_snooze or test_am_pm',
        '--tb', 'short'
    ])


def run_all_tests() -> dict:
    """Run all test suites and return results"""
    results = {}

    print("\n" + "="*70)
    print(" SMS REMINDERS - COMPREHENSIVE TEST SUITE")
    print("="*70)

    # Unit tests
    print("\n[1/4] Running Unit Tests...")
    results['unit'] = run_unit_tests() == 0

    # Integration tests (may skip if no DB)
    print("\n[2/4] Running Integration Tests...")
    results['integration'] = run_integration_tests() == 0

    # Journey tests
    print("\n[3/4] Running User Journey Tests...")
    results['journeys'] = run_journey_tests() == 0

    # Quick stress test
    print("\n[4/4] Running Stress Test (5 users, 10 messages)...")
    results['stress'] = run_stress_tests(users=5, messages=10, workers=3) == 0

    # Summary
    print("\n" + "="*70)
    print(" TEST RESULTS SUMMARY")
    print("="*70)

    for suite, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        icon = "[OK]" if passed else "[X]"
        print(f"  {icon} {suite.upper()}: {status}")

    all_passed = all(results.values())
    print("\n" + ("All tests PASSED!" if all_passed else "Some tests FAILED!"))
    print("="*70)

    return results


def check_dependencies() -> bool:
    """Check if required dependencies are installed"""
    required = ['pytest', 'fastapi']
    missing = []

    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install pytest pytest-cov")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="SMS Reminders Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/run_tests.py                    # Run all tests
  python tests/run_tests.py --suite unit       # Run unit tests only
  python tests/run_tests.py --smoke            # Quick smoke test
  python tests/run_tests.py --stress --users 100  # Stress test with 100 users
        """
    )

    parser.add_argument('--suite', type=str,
                       choices=['unit', 'integration', 'journeys', 'stress', 'all'],
                       default='all',
                       help='Test suite to run')

    parser.add_argument('--smoke', action='store_true',
                       help='Run quick smoke tests')

    parser.add_argument('--stress', action='store_true',
                       help='Run stress simulation')

    parser.add_argument('--users', type=int, default=10,
                       help='Number of simulated users for stress test')

    parser.add_argument('--messages', type=int, default=20,
                       help='Messages per user for stress test')

    parser.add_argument('--workers', type=int, default=5,
                       help='Concurrent workers for stress test')

    parser.add_argument('--html-report', action='store_true',
                       help='Generate HTML report (requires pytest-html)')

    parser.add_argument('--coverage', action='store_true',
                       help='Run with coverage (requires pytest-cov)')

    args = parser.parse_args()

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Change to project root
    os.chdir(Path(__file__).parent.parent)

    # Run appropriate tests
    exit_code = 0

    if args.smoke:
        exit_code = run_smoke_tests()

    elif args.stress:
        exit_code = run_stress_tests(args.users, args.messages, args.workers)

    elif args.suite == 'unit':
        exit_code = run_unit_tests()

    elif args.suite == 'integration':
        exit_code = run_integration_tests()

    elif args.suite == 'journeys':
        exit_code = run_journey_tests()

    elif args.suite == 'stress':
        exit_code = run_stress_tests(args.users, args.messages, args.workers)

    elif args.suite == 'all':
        results = run_all_tests()
        exit_code = 0 if all(results.values()) else 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
