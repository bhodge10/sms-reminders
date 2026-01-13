#!/usr/bin/env python3
"""
SMS Reminders Stress Test Suite
Simulates real user interactions to test all functionality.

Usage:
    # Run all tests
    python -m pytest tests/stress_test.py -v

    # Run with coverage
    python -m pytest tests/stress_test.py -v --cov=.

    # Run specific test category
    python -m pytest tests/stress_test.py -v -k "onboarding"

    # Run stress simulation
    python tests/stress_test.py --simulate --users 50 --messages 100
"""

import os
import sys
import json
import time
import random
import argparse
import threading
import concurrent.futures
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TestResult:
    """Represents the result of a single test interaction"""
    phone_number: str
    message_sent: str
    response_received: str
    expected_behavior: str
    passed: bool
    error: Optional[str] = None
    response_time_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {
            'phone_number': self.phone_number,
            'message_sent': self.message_sent,
            'response_received': self.response_received[:200] if self.response_received else None,
            'expected_behavior': self.expected_behavior,
            'passed': self.passed,
            'error': self.error,
            'response_time_ms': self.response_time_ms,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class TestReport:
    """Aggregated test report"""
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    avg_response_time_ms: float = 0
    results: List[TestResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    categories: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: {'passed': 0, 'failed': 0}))

    def add_result(self, result: TestResult, category: str = "general"):
        self.results.append(result)
        self.total_tests += 1
        if result.passed:
            self.passed += 1
            self.categories[category]['passed'] += 1
        elif result.error:
            self.errors += 1
            self.categories[category]['failed'] += 1
        else:
            self.failed += 1
            self.categories[category]['failed'] += 1

    def finalize(self):
        self.end_time = datetime.now()
        if self.results:
            self.avg_response_time_ms = sum(r.response_time_ms for r in self.results) / len(self.results)

    def summary(self) -> str:
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        lines = [
            "\n" + "=" * 60,
            "STRESS TEST REPORT",
            "=" * 60,
            f"Duration: {duration:.2f}s",
            f"Total Tests: {self.total_tests}",
            f"Passed: {self.passed} ({100*self.passed/max(1,self.total_tests):.1f}%)",
            f"Failed: {self.failed} ({100*self.failed/max(1,self.total_tests):.1f}%)",
            f"Errors: {self.errors} ({100*self.errors/max(1,self.total_tests):.1f}%)",
            f"Avg Response Time: {self.avg_response_time_ms:.2f}ms",
            "",
            "BY CATEGORY:",
        ]
        for cat, stats in self.categories.items():
            total = stats['passed'] + stats['failed']
            pct = 100 * stats['passed'] / max(1, total)
            lines.append(f"  {cat}: {stats['passed']}/{total} ({pct:.1f}%)")

        if self.failed > 0:
            lines.extend(["", "FAILED TESTS:"])
            for r in self.results:
                if not r.passed:
                    lines.append(f"  - [{r.phone_number}] '{r.message_sent[:50]}...'")
                    lines.append(f"    Expected: {r.expected_behavior}")
                    lines.append(f"    Got: {r.response_received[:100]}..." if r.response_received else "    Got: (no response)")
                    if r.error:
                        lines.append(f"    Error: {r.error}")

        lines.append("=" * 60)
        return "\n".join(lines)


# ============================================================================
# SMS SIMULATOR
# ============================================================================

class SMSSimulator:
    """
    Simulates SMS interactions with the service.
    Can use the real FastAPI endpoint or mock responses.
    """

    def __init__(self, use_real_endpoint=False, base_url=None):
        self.use_real_endpoint = use_real_endpoint
        self.base_url = base_url or "http://localhost:8000"
        self.report = TestReport()
        self._client = None

    @property
    def client(self):
        """Lazy-load the test client"""
        if self._client is None:
            if self.use_real_endpoint:
                import requests
                self._client = requests
            else:
                from fastapi.testclient import TestClient
                from main import app
                self._client = TestClient(app)
        return self._client

    def send_sms(self, phone_number: str, message: str) -> tuple:
        """
        Send an SMS message and get the response.
        Returns (response_text, response_time_ms)
        """
        start_time = time.time()

        try:
            if self.use_real_endpoint:
                response = self.client.post(
                    f"{self.base_url}/sms",
                    data={"Body": message, "From": phone_number},
                    timeout=30
                )
            else:
                response = self.client.post(
                    "/sms",
                    data={"Body": message, "From": phone_number}
                )

            response_time_ms = (time.time() - start_time) * 1000

            # Parse TwiML response to extract message
            response_text = self._extract_message_from_twiml(response.text)

            return response_text, response_time_ms

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return f"ERROR: {str(e)}", response_time_ms

    def _extract_message_from_twiml(self, twiml: str) -> str:
        """Extract the message text from TwiML response"""
        import re
        # Match content between <Message> tags
        match = re.search(r'<Message>(.*?)</Message>', twiml, re.DOTALL)
        if match:
            return match.group(1).strip()
        return twiml

    def run_test(self, phone_number: str, message: str,
                 expected_behavior: str, validator=None, category="general") -> TestResult:
        """
        Run a single test and validate the response.

        Args:
            phone_number: The test phone number
            message: The message to send
            expected_behavior: Description of expected behavior
            validator: Optional function(response) -> bool to validate response
            category: Category for reporting

        Returns:
            TestResult object
        """
        response, response_time = self.send_sms(phone_number, message)

        passed = True
        error = None

        if response.startswith("ERROR:"):
            passed = False
            error = response

        elif validator:
            try:
                passed = validator(response)
            except Exception as e:
                passed = False
                error = f"Validator error: {str(e)}"

        result = TestResult(
            phone_number=phone_number,
            message_sent=message,
            response_received=response,
            expected_behavior=expected_behavior,
            passed=passed,
            error=error,
            response_time_ms=response_time
        )

        self.report.add_result(result, category)
        return result


# ============================================================================
# RESPONSE VALIDATORS
# ============================================================================

class ResponseValidators:
    """Collection of response validation functions"""

    @staticmethod
    def contains(text: str):
        """Validator that checks if response contains specific text"""
        def validator(response: str) -> bool:
            return text.lower() in response.lower()
        return validator

    @staticmethod
    def contains_any(*texts):
        """Validator that checks if response contains any of the texts"""
        def validator(response: str) -> bool:
            response_lower = response.lower()
            return any(t.lower() in response_lower for t in texts)
        return validator

    @staticmethod
    def contains_all(*texts):
        """Validator that checks if response contains all of the texts"""
        def validator(response: str) -> bool:
            response_lower = response.lower()
            return all(t.lower() in response_lower for t in texts)
        return validator

    @staticmethod
    def not_contains(text: str):
        """Validator that checks if response does NOT contain specific text"""
        def validator(response: str) -> bool:
            return text.lower() not in response.lower()
        return validator

    @staticmethod
    def is_not_error():
        """Validator that checks response is not an error"""
        def validator(response: str) -> bool:
            error_indicators = ['error', 'sorry', 'trouble', 'failed', 'couldn\'t']
            response_lower = response.lower()
            return not any(e in response_lower for e in error_indicators)
        return validator

    @staticmethod
    def matches_pattern(pattern: str):
        """Validator using regex pattern"""
        import re
        def validator(response: str) -> bool:
            return bool(re.search(pattern, response, re.IGNORECASE))
        return validator

    @staticmethod
    def length_between(min_len: int, max_len: int):
        """Validator that checks response length"""
        def validator(response: str) -> bool:
            return min_len <= len(response) <= max_len
        return validator

    @staticmethod
    def is_reminder_confirmation():
        """Validator for reminder confirmation responses"""
        def validator(response: str) -> bool:
            indicators = ["remind you", "i'll remind", "reminder set", "scheduled"]
            return any(i in response.lower() for i in indicators)
        return validator

    @staticmethod
    def is_memory_confirmation():
        """Validator for memory storage confirmation"""
        def validator(response: str) -> bool:
            indicators = ["remember", "stored", "saved", "got it", "noted"]
            return any(i in response.lower() for i in indicators)
        return validator

    @staticmethod
    def is_list_response():
        """Validator for list-related responses"""
        def validator(response: str) -> bool:
            indicators = ["list", "added", "created", "checked", "items"]
            return any(i in response.lower() for i in indicators)
        return validator

    @staticmethod
    def asks_clarification():
        """Validator that checks if service is asking for clarification"""
        def validator(response: str) -> bool:
            indicators = ["am or pm", "which", "what time", "please specify", "?"]
            return any(i in response.lower() for i in indicators)
        return validator


# ============================================================================
# TEST SCENARIOS
# ============================================================================

class TestScenarios:
    """
    Collection of test scenarios organized by feature.
    Each scenario is a tuple: (message, expected_behavior, validator, category)
    """

    @staticmethod
    def get_onboarding_flow(user_data: dict) -> List[tuple]:
        """Complete onboarding flow for a new user"""
        return [
            (user_data.get('first_name', 'John'),
             "Should accept first name",
             ResponseValidators.contains_any('last name', 'surname', 'family name'),
             "onboarding"),

            (user_data.get('last_name', 'Doe'),
             "Should accept last name and ask for email",
             ResponseValidators.contains_any('email', '@'),
             "onboarding"),

            (user_data.get('email', 'test@example.com'),
             "Should accept email and ask for zip",
             ResponseValidators.contains_any('zip', 'postal', 'code'),
             "onboarding"),

            (user_data.get('zip_code', '10001'),
             "Should detect timezone from zip",
             ResponseValidators.contains_any('timezone', 'time zone', 'daily summary'),
             "onboarding"),

            ("yes",
             "Should complete onboarding",
             ResponseValidators.contains_any('ready', 'help', 'started', 'welcome'),
             "onboarding"),
        ]

    @staticmethod
    def get_memory_tests() -> List[tuple]:
        """Test scenarios for memory storage and retrieval"""
        return [
            ("Remember my wifi password is HomeNetwork123",
             "Should store memory",
             ResponseValidators.is_memory_confirmation(),
             "memory"),

            ("Remember my car is a 2020 Honda Civic",
             "Should store memory about car",
             ResponseValidators.is_memory_confirmation(),
             "memory"),

            ("Store that my doctor's number is 555-1234",
             "Should store doctor's number",
             ResponseValidators.is_memory_confirmation(),
             "memory"),

            ("My memories",
             "Should list stored memories",
             ResponseValidators.contains_any('wifi', 'car', 'doctor', 'memories'),
             "memory"),

            ("What's my wifi password?",
             "Should retrieve wifi password",
             ResponseValidators.contains("HomeNetwork123"),
             "memory"),

            ("What car do I have?",
             "Should retrieve car info",
             ResponseValidators.contains_any("honda", "civic", "2020"),
             "memory"),
        ]

    @staticmethod
    def get_reminder_tests() -> List[tuple]:
        """Test scenarios for reminder operations"""
        return [
            # Specific time reminders
            ("Remind me at 9pm to take medicine",
             "Should set reminder for 9pm",
             ResponseValidators.is_reminder_confirmation(),
             "reminder"),

            ("Remind me at 8:30am to call mom",
             "Should set reminder for 8:30am",
             ResponseValidators.is_reminder_confirmation(),
             "reminder"),

            ("Remind me tomorrow at 3pm to go shopping",
             "Should set reminder for tomorrow",
             ResponseValidators.contains_any("tomorrow", "remind"),
             "reminder"),

            # Relative time reminders
            ("Remind me in 30 minutes to check the oven",
             "Should set reminder for 30 minutes from now",
             ResponseValidators.is_reminder_confirmation(),
             "reminder"),

            ("Remind me in 2 hours to call back",
             "Should set reminder for 2 hours from now",
             ResponseValidators.is_reminder_confirmation(),
             "reminder"),

            ("Remind me in 3 days to follow up",
             "Should set reminder for 3 days from now",
             ResponseValidators.is_reminder_confirmation(),
             "reminder"),

            # List reminders
            ("My reminders",
             "Should list pending reminders",
             ResponseValidators.contains_any("reminder", "scheduled", "pending", "no reminder"),
             "reminder"),
        ]

    @staticmethod
    def get_recurring_reminder_tests() -> List[tuple]:
        """Test scenarios for recurring reminders"""
        return [
            ("Remind me every day at 7pm to take medicine",
             "Should create daily recurring reminder",
             ResponseValidators.contains_any("every day", "daily", "recurring", "remind"),
             "recurring"),

            ("Every Sunday at 6pm remind me to take out garbage",
             "Should create weekly recurring reminder",
             ResponseValidators.contains_any("sunday", "weekly", "recurring", "remind"),
             "recurring"),

            ("Remind me every weekday at 8am to check email",
             "Should create weekday recurring reminder",
             ResponseValidators.contains_any("weekday", "recurring", "remind"),
             "recurring"),

            ("My recurring",
             "Should list recurring reminders",
             ResponseValidators.contains_any("recurring", "daily", "weekly", "none", "no recurring"),
             "recurring"),
        ]

    @staticmethod
    def get_ambiguous_time_tests() -> List[tuple]:
        """Test scenarios for ambiguous time handling"""
        return [
            ("Remind me at 9 to take medicine",
             "Should ask for AM/PM clarification",
             ResponseValidators.asks_clarification(),
             "clarification"),

            ("AM",
             "Should confirm reminder for 9 AM",
             ResponseValidators.is_reminder_confirmation(),
             "clarification"),

            ("Remind me at 4:30 to call wife",
             "Should ask for AM/PM clarification",
             ResponseValidators.asks_clarification(),
             "clarification"),

            ("PM",
             "Should confirm reminder for 4:30 PM",
             ResponseValidators.is_reminder_confirmation(),
             "clarification"),
        ]

    @staticmethod
    def get_list_tests() -> List[tuple]:
        """Test scenarios for list operations"""
        return [
            ("Create a grocery list",
             "Should create grocery list",
             ResponseValidators.is_list_response(),
             "list"),

            ("Add milk, eggs, bread to grocery list",
             "Should add items to grocery list",
             ResponseValidators.contains_any("added", "milk", "eggs", "bread"),
             "list"),

            ("Add butter to grocery list",
             "Should add butter to grocery list",
             ResponseValidators.contains("butter"),
             "list"),

            ("Show grocery list",
             "Should display grocery list",
             ResponseValidators.contains_any("milk", "eggs", "bread", "butter", "grocery"),
             "list"),

            ("Check off milk",
             "Should mark milk as complete",
             ResponseValidators.contains_any("checked", "complete", "done", "milk"),
             "list"),

            ("My lists",
             "Should show all lists",
             ResponseValidators.contains_any("grocery", "list"),
             "list"),
        ]

    @staticmethod
    def get_help_tests() -> List[tuple]:
        """Test scenarios for help and info commands"""
        return [
            ("Help",
             "Should provide help information",
             ResponseValidators.contains_any("help", "remind", "memory", "list", "guide"),
             "help"),

            ("?",
             "Should provide help information",
             ResponseValidators.contains_any("help", "remind", "memory", "list", "guide", "info"),
             "help"),

            ("Info",
             "Should provide service information",
             ResponseValidators.length_between(50, 2000),
             "help"),

            ("Commands",
             "Should list available commands",
             ResponseValidators.length_between(50, 2000),
             "help"),
        ]

    @staticmethod
    def get_account_tests() -> List[tuple]:
        """Test scenarios for account management"""
        return [
            ("My timezone",
             "Should show current timezone",
             ResponseValidators.contains_any("timezone", "time zone", "america", "pacific", "eastern"),
             "account"),

            ("My account",
             "Should show account info or upgrade options",
             ResponseValidators.contains_any("account", "subscription", "premium", "upgrade", "manage"),
             "account"),

            ("My summary",
             "Should show summary status",
             ResponseValidators.contains_any("summary", "daily", "enabled", "disabled"),
             "account"),
        ]

    @staticmethod
    def get_edge_case_tests() -> List[tuple]:
        """Test scenarios for edge cases and error handling"""
        return [
            ("",
             "Should handle empty message gracefully",
             ResponseValidators.length_between(1, 500),
             "edge_case"),

            ("   ",
             "Should handle whitespace-only message",
             ResponseValidators.length_between(1, 500),
             "edge_case"),

            ("a" * 500,
             "Should handle very long message",
             ResponseValidators.not_contains("error"),
             "edge_case"),

            ("Remind me at 25:00pm to do something",
             "Should handle invalid time gracefully",
             ResponseValidators.not_contains("crash"),
             "edge_case"),

            ("!!!@@@###$$$",
             "Should handle special characters",
             ResponseValidators.length_between(1, 500),
             "edge_case"),

            ("1234567890",
             "Should handle numbers-only message",
             ResponseValidators.length_between(1, 500),
             "edge_case"),
        ]

    @staticmethod
    def get_snooze_tests() -> List[tuple]:
        """Test scenarios for snooze functionality"""
        return [
            ("Snooze",
             "Should snooze or indicate no recent reminder",
             ResponseValidators.contains_any("snooze", "snoozed", "no reminder", "nothing to snooze"),
             "snooze"),

            ("Snooze 30",
             "Should snooze for 30 minutes or indicate error",
             ResponseValidators.contains_any("snooze", "snoozed", "30", "minute", "no reminder"),
             "snooze"),

            ("Snooze 1h",
             "Should snooze for 1 hour or indicate error",
             ResponseValidators.contains_any("snooze", "snoozed", "hour", "no reminder"),
             "snooze"),
        ]


# ============================================================================
# PYTEST TEST CLASSES
# ============================================================================

class TestOnboarding:
    """Test cases for user onboarding flow"""

    @pytest.fixture(autouse=True)
    def setup(self, app_client):
        self.simulator = SMSSimulator(use_real_endpoint=False)
        self.simulator._client = app_client
        self.phone = f"+1555{random.randint(1000000, 9999999)}"

    def test_complete_onboarding(self, test_user_data):
        """Test complete onboarding flow from start to finish"""
        scenarios = TestScenarios.get_onboarding_flow(test_user_data)

        for message, expected, validator, category in scenarios:
            result = self.simulator.run_test(
                self.phone, message, expected, validator, category
            )
            # Continue even if one step fails to see full flow
            if not result.passed:
                print(f"Failed at step: {message}")
                print(f"Response: {result.response_received}")


class TestMemories:
    """Test cases for memory storage and retrieval"""

    @pytest.fixture(autouse=True)
    def setup(self, app_client):
        self.simulator = SMSSimulator(use_real_endpoint=False)
        self.simulator._client = app_client
        self.phone = f"+1555{random.randint(1000000, 9999999)}"

        # Complete onboarding first
        onboarding_messages = ["John", "Doe", "test@example.com", "10001", "yes"]
        for msg in onboarding_messages:
            self.simulator.send_sms(self.phone, msg)

    def test_memory_storage_and_retrieval(self):
        """Test storing and retrieving memories"""
        scenarios = TestScenarios.get_memory_tests()

        for message, expected, validator, category in scenarios:
            result = self.simulator.run_test(
                self.phone, message, expected, validator, category
            )
            assert result.passed, f"Failed: {message} - Got: {result.response_received}"


class TestReminders:
    """Test cases for reminder functionality"""

    @pytest.fixture(autouse=True)
    def setup(self, app_client):
        self.simulator = SMSSimulator(use_real_endpoint=False)
        self.simulator._client = app_client
        self.phone = f"+1555{random.randint(1000000, 9999999)}"

        # Complete onboarding first
        onboarding_messages = ["John", "Doe", "test@example.com", "10001", "yes"]
        for msg in onboarding_messages:
            self.simulator.send_sms(self.phone, msg)

    def test_specific_time_reminders(self):
        """Test reminders with specific times"""
        tests = [
            ("Remind me at 9pm to take medicine",
             ResponseValidators.is_reminder_confirmation()),
            ("Remind me at 8:30am to call mom",
             ResponseValidators.is_reminder_confirmation()),
        ]

        for message, validator in tests:
            result = self.simulator.run_test(
                self.phone, message, "Should create reminder", validator, "reminder"
            )
            assert result.passed, f"Failed: {message}"

    def test_relative_time_reminders(self):
        """Test reminders with relative times"""
        tests = [
            ("Remind me in 30 minutes to check oven",
             ResponseValidators.is_reminder_confirmation()),
            ("Remind me in 2 hours to call back",
             ResponseValidators.is_reminder_confirmation()),
        ]

        for message, validator in tests:
            result = self.simulator.run_test(
                self.phone, message, "Should create reminder", validator, "reminder"
            )
            assert result.passed, f"Failed: {message}"


class TestLists:
    """Test cases for list functionality"""

    @pytest.fixture(autouse=True)
    def setup(self, app_client):
        self.simulator = SMSSimulator(use_real_endpoint=False)
        self.simulator._client = app_client
        self.phone = f"+1555{random.randint(1000000, 9999999)}"

        # Complete onboarding first
        onboarding_messages = ["John", "Doe", "test@example.com", "10001", "yes"]
        for msg in onboarding_messages:
            self.simulator.send_sms(self.phone, msg)

    def test_list_operations(self):
        """Test list creation and management"""
        scenarios = TestScenarios.get_list_tests()

        for message, expected, validator, category in scenarios:
            result = self.simulator.run_test(
                self.phone, message, expected, validator, category
            )
            # Don't assert - collect results
            if not result.passed:
                print(f"Note: {message} - {result.response_received[:100]}")


class TestEdgeCases:
    """Test cases for edge cases and error handling"""

    @pytest.fixture(autouse=True)
    def setup(self, app_client):
        self.simulator = SMSSimulator(use_real_endpoint=False)
        self.simulator._client = app_client
        self.phone = f"+1555{random.randint(1000000, 9999999)}"

        # Complete onboarding first
        onboarding_messages = ["John", "Doe", "test@example.com", "10001", "yes"]
        for msg in onboarding_messages:
            self.simulator.send_sms(self.phone, msg)

    def test_edge_cases(self):
        """Test edge cases don't crash the service"""
        scenarios = TestScenarios.get_edge_case_tests()

        for message, expected, validator, category in scenarios:
            result = self.simulator.run_test(
                self.phone, message, expected, validator, category
            )
            # Edge cases should at least not crash
            assert "ERROR" not in result.response_received or "error" not in result.response_received.lower()


# ============================================================================
# STRESS TEST RUNNER
# ============================================================================

class StressTestRunner:
    """
    Runs comprehensive stress tests simulating multiple concurrent users.
    """

    def __init__(self, num_users=10, messages_per_user=20, use_real_endpoint=False):
        self.num_users = num_users
        self.messages_per_user = messages_per_user
        self.use_real_endpoint = use_real_endpoint
        self.report = TestReport()
        self.lock = threading.Lock()

    def generate_phone_number(self, index: int) -> str:
        """Generate a unique test phone number"""
        return f"+1555{str(index).zfill(7)}"

    def get_random_message_sequence(self) -> List[tuple]:
        """Generate a random sequence of test messages for a user"""
        all_scenarios = []

        # Always include onboarding
        all_scenarios.extend(TestScenarios.get_onboarding_flow({
            'first_name': f"Test{random.randint(1, 999)}",
            'last_name': 'User',
            'email': f"test{random.randint(1, 9999)}@example.com",
            'zip_code': random.choice(['10001', '90210', '60601', '98101', '30301'])
        }))

        # Add random mix of other scenarios
        scenario_pools = [
            TestScenarios.get_memory_tests(),
            TestScenarios.get_reminder_tests(),
            TestScenarios.get_recurring_reminder_tests(),
            TestScenarios.get_list_tests(),
            TestScenarios.get_help_tests(),
            TestScenarios.get_account_tests(),
            TestScenarios.get_snooze_tests(),
        ]

        # Sample from each pool
        for pool in scenario_pools:
            sample_size = min(len(pool), random.randint(1, 3))
            all_scenarios.extend(random.sample(pool, sample_size))

        # Optionally add edge cases
        if random.random() < 0.3:  # 30% chance
            all_scenarios.extend(random.sample(
                TestScenarios.get_edge_case_tests(),
                min(2, len(TestScenarios.get_edge_case_tests()))
            ))

        return all_scenarios

    def simulate_user(self, user_index: int) -> List[TestResult]:
        """Simulate a single user's interaction session"""
        phone = self.generate_phone_number(user_index)
        simulator = SMSSimulator(use_real_endpoint=self.use_real_endpoint)
        results = []

        scenarios = self.get_random_message_sequence()

        for message, expected, validator, category in scenarios[:self.messages_per_user]:
            # Random delay to simulate real user behavior
            time.sleep(random.uniform(0.1, 0.5))

            result = simulator.run_test(phone, message, expected, validator, category)
            results.append(result)

            with self.lock:
                self.report.add_result(result, category)

        return results

    def run(self, max_workers=5) -> TestReport:
        """Run the stress test with multiple concurrent users"""
        print(f"\nStarting stress test: {self.num_users} users, "
              f"{self.messages_per_user} messages each, {max_workers} workers")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.simulate_user, i)
                for i in range(self.num_users)
            ]

            # Wait for all to complete with progress
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                completed += 1
                print(f"\rProgress: {completed}/{self.num_users} users", end="", flush=True)

        print()  # New line after progress
        self.report.finalize()
        return self.report


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="SMS Reminders Stress Test Suite")
    parser.add_argument('--simulate', action='store_true',
                       help='Run stress simulation with concurrent users')
    parser.add_argument('--users', type=int, default=10,
                       help='Number of simulated users (default: 10)')
    parser.add_argument('--messages', type=int, default=20,
                       help='Messages per user (default: 20)')
    parser.add_argument('--workers', type=int, default=5,
                       help='Concurrent workers (default: 5)')
    parser.add_argument('--real', action='store_true',
                       help='Use real HTTP endpoint instead of test client')
    parser.add_argument('--url', type=str, default='http://localhost:8000',
                       help='Base URL for real endpoint testing')
    parser.add_argument('--output', type=str,
                       help='Output file for JSON report')

    args = parser.parse_args()

    if args.simulate:
        runner = StressTestRunner(
            num_users=args.users,
            messages_per_user=args.messages,
            use_real_endpoint=args.real
        )
        report = runner.run(max_workers=args.workers)
        print(report.summary())

        if args.output:
            with open(args.output, 'w') as f:
                json.dump({
                    'summary': {
                        'total': report.total_tests,
                        'passed': report.passed,
                        'failed': report.failed,
                        'errors': report.errors,
                        'avg_response_time_ms': report.avg_response_time_ms,
                        'duration_seconds': (report.end_time - report.start_time).total_seconds() if report.end_time else 0
                    },
                    'categories': dict(report.categories),
                    'failed_tests': [r.to_dict() for r in report.results if not r.passed]
                }, f, indent=2)
            print(f"\nReport saved to: {args.output}")
    else:
        # Run pytest
        pytest.main([__file__, '-v'])


if __name__ == "__main__":
    main()
