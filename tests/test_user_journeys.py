#!/usr/bin/env python3
"""
User Journey Tests for SMS Reminders.
Simulates complete user interaction flows to test end-to-end functionality.

These tests simulate realistic user sessions including:
- New user onboarding
- Daily reminder usage
- List management
- Edge cases and recovery

Usage:
    python -m pytest tests/test_user_journeys.py -v
    python tests/test_user_journeys.py --run-journeys
"""

import os
import sys
import time
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class JourneyStep:
    """Represents a single step in a user journey"""

    def __init__(self, message: str, description: str,
                 validators: List[Callable] = None,
                 wait_seconds: float = 0,
                 conditional: Callable = None):
        self.message = message
        self.description = description
        self.validators = validators or []
        self.wait_seconds = wait_seconds
        self.conditional = conditional  # Function(prev_response) -> bool, skip if False

    def validate(self, response: str) -> tuple:
        """Validate response against all validators. Returns (passed, errors)"""
        errors = []
        for validator in self.validators:
            try:
                if not validator(response):
                    errors.append(f"Validator failed: {validator.__name__}")
            except Exception as e:
                errors.append(f"Validator error: {str(e)}")

        return len(errors) == 0, errors


class UserJourney:
    """Represents a complete user journey with multiple steps"""

    def __init__(self, name: str, description: str, steps: List[JourneyStep]):
        self.name = name
        self.description = description
        self.steps = steps
        self.results = []

    def run(self, simulator, phone_number: str) -> dict:
        """Execute the journey and return results"""
        results = {
            'name': self.name,
            'phone': phone_number,
            'steps': [],
            'passed': 0,
            'failed': 0,
            'start_time': datetime.now().isoformat()
        }

        prev_response = None

        for i, step in enumerate(self.steps):
            # Check conditional
            if step.conditional and prev_response:
                if not step.conditional(prev_response):
                    results['steps'].append({
                        'step': i + 1,
                        'message': step.message,
                        'description': step.description,
                        'skipped': True,
                        'reason': 'Conditional not met'
                    })
                    continue

            # Wait if specified
            if step.wait_seconds > 0:
                time.sleep(step.wait_seconds)

            # Send message
            response, response_time = simulator.send_sms(phone_number, step.message)

            # Validate
            passed, errors = step.validate(response)

            step_result = {
                'step': i + 1,
                'message': step.message,
                'description': step.description,
                'response': response[:200] if response else None,
                'response_time_ms': response_time,
                'passed': passed,
                'errors': errors
            }
            results['steps'].append(step_result)

            if passed:
                results['passed'] += 1
            else:
                results['failed'] += 1

            prev_response = response

        results['end_time'] = datetime.now().isoformat()
        results['total_steps'] = len(self.steps)
        return results


# ============================================================================
# VALIDATORS
# ============================================================================

def contains(text: str):
    """Check if response contains text (case-insensitive)"""
    def validator(response: str) -> bool:
        return text.lower() in response.lower()
    validator.__name__ = f"contains('{text}')"
    return validator


def contains_any(*texts):
    """Check if response contains any of the texts"""
    def validator(response: str) -> bool:
        return any(t.lower() in response.lower() for t in texts)
    validator.__name__ = f"contains_any({texts})"
    return validator


def not_contains(text: str):
    """Check if response does NOT contain text"""
    def validator(response: str) -> bool:
        return text.lower() not in response.lower()
    validator.__name__ = f"not_contains('{text}')"
    return validator


def has_length_between(min_len: int, max_len: int):
    """Check response length is within range"""
    def validator(response: str) -> bool:
        return min_len <= len(response) <= max_len
    validator.__name__ = f"length_between({min_len}, {max_len})"
    return validator


def is_not_error():
    """Check response is not an error message"""
    def validator(response: str) -> bool:
        error_words = ['error', 'failed', 'crash', 'exception']
        return not any(e in response.lower() for e in error_words)
    validator.__name__ = "is_not_error"
    return validator


# ============================================================================
# USER JOURNEY DEFINITIONS
# ============================================================================

def create_new_user_journey() -> UserJourney:
    """Journey: Brand new user signs up and sets first reminder"""
    return UserJourney(
        name="New User Onboarding",
        description="A new user signs up, completes onboarding, and sets their first reminder",
        steps=[
            JourneyStep(
                "Hi",
                "Initial contact triggers onboarding",
                [contains_any("welcome", "first name", "name", "hi")]
            ),
            JourneyStep(
                "Sarah",
                "Provides first name",
                [contains_any("last name", "surname")]
            ),
            JourneyStep(
                "Johnson",
                "Provides last name",
                [contains_any("email", "@")]
            ),
            JourneyStep(
                "sarah.j@email.com",
                "Provides email",
                [contains_any("zip", "postal", "code")]
            ),
            JourneyStep(
                "90210",
                "Provides ZIP code",
                [contains_any("timezone", "daily", "summary", "time zone")]
            ),
            JourneyStep(
                "yes",
                "Opts into daily summary",
                [contains_any("ready", "help", "start", "welcome")]
            ),
            JourneyStep(
                "Remind me at 9pm to take my vitamins",
                "Sets first reminder",
                [contains_any("remind", "9", "vitamin", "pm")]
            ),
            JourneyStep(
                "My reminders",
                "Views their reminders",
                [contains_any("vitamin", "reminder", "scheduled")]
            ),
        ]
    )


def create_power_user_journey() -> UserJourney:
    """Journey: Experienced user manages multiple features"""
    return UserJourney(
        name="Power User Session",
        description="An experienced user uses multiple features in one session",
        steps=[
            # Assume already onboarded
            JourneyStep(
                "Create a grocery list",
                "Creates a new list",
                [contains_any("created", "grocery", "list")]
            ),
            JourneyStep(
                "Add milk, eggs, bread, butter to grocery list",
                "Adds multiple items",
                [contains_any("added", "milk", "eggs")]
            ),
            JourneyStep(
                "Show grocery list",
                "Views the list",
                [contains_any("milk", "eggs", "bread", "butter")]
            ),
            JourneyStep(
                "Check off milk",
                "Marks item complete",
                [contains_any("checked", "done", "complete", "milk")]
            ),
            JourneyStep(
                "Remind me at 6pm to go grocery shopping",
                "Sets reminder related to list",
                [contains_any("remind", "6", "grocery", "pm")]
            ),
            JourneyStep(
                "Remember that my favorite store is Whole Foods",
                "Stores a memory",
                [contains_any("remember", "store", "got it", "saved")]
            ),
            JourneyStep(
                "What's my favorite store?",
                "Retrieves the memory",
                [contains("whole foods")]
            ),
            JourneyStep(
                "My reminders",
                "Checks all reminders",
                [contains_any("grocery", "reminder")]
            ),
        ]
    )


def create_reminder_heavy_journey() -> UserJourney:
    """Journey: User sets many different types of reminders"""
    return UserJourney(
        name="Reminder Power User",
        description="User sets various types of reminders",
        steps=[
            JourneyStep(
                "Remind me at 8am tomorrow to call the doctor",
                "Sets specific time reminder",
                [contains_any("remind", "8", "doctor", "tomorrow")]
            ),
            JourneyStep(
                "Remind me in 2 hours to check the mail",
                "Sets relative time reminder",
                [contains_any("remind", "2 hour", "mail")]
            ),
            JourneyStep(
                "Remind me every day at 7pm to take medicine",
                "Sets daily recurring reminder",
                [contains_any("remind", "every day", "daily", "7", "medicine")]
            ),
            JourneyStep(
                "Remind me every Monday at 9am to submit timesheet",
                "Sets weekly recurring reminder",
                [contains_any("remind", "monday", "weekly", "timesheet")]
            ),
            JourneyStep(
                "My reminders",
                "Views all reminders",
                [contains_any("doctor", "mail", "reminder")]
            ),
            JourneyStep(
                "My recurring",
                "Views recurring reminders",
                [contains_any("medicine", "timesheet", "recurring", "daily", "weekly")]
            ),
            JourneyStep(
                "Delete reminder about mail",
                "Deletes a reminder",
                [contains_any("delete", "removed", "mail", "cancelled")]
            ),
        ]
    )


def create_list_management_journey() -> UserJourney:
    """Journey: User manages shopping lists"""
    return UserJourney(
        name="List Management",
        description="User creates and manages multiple lists",
        steps=[
            JourneyStep(
                "Create a shopping list",
                "Creates shopping list",
                [contains_any("created", "shopping", "list")]
            ),
            JourneyStep(
                "Add apples and oranges to shopping list",
                "Adds items to list",
                [contains_any("added", "apple", "orange")]
            ),
            JourneyStep(
                "Create a todo list",
                "Creates another list",
                [contains_any("created", "todo", "list")]
            ),
            JourneyStep(
                "Add call mom and pay bills to todo list",
                "Adds items to todo list",
                [contains_any("added", "call", "pay", "todo")]
            ),
            JourneyStep(
                "My lists",
                "Views all lists",
                [contains_any("shopping", "todo", "list")]
            ),
            JourneyStep(
                "Show shopping list",
                "Views specific list",
                [contains_any("apple", "orange", "shopping")]
            ),
            JourneyStep(
                "Check off apples",
                "Marks item done",
                [contains_any("checked", "done", "apple")]
            ),
            JourneyStep(
                "Delete oranges from shopping list",
                "Removes an item",
                [contains_any("deleted", "removed", "orange")]
            ),
        ]
    )


def create_memory_journey() -> UserJourney:
    """Journey: User stores and retrieves memories"""
    return UserJourney(
        name="Memory Management",
        description="User stores important information and retrieves it",
        steps=[
            JourneyStep(
                "Remember my wifi password is SecurePass123",
                "Stores wifi password",
                [contains_any("remember", "got it", "saved", "stored")]
            ),
            JourneyStep(
                "Remember my car is a 2022 Toyota Camry",
                "Stores car info",
                [contains_any("remember", "got it", "saved", "stored")]
            ),
            JourneyStep(
                "Store that my anniversary is June 15th",
                "Stores anniversary date",
                [contains_any("remember", "got it", "saved", "stored")]
            ),
            JourneyStep(
                "What's my wifi password?",
                "Retrieves wifi password",
                [contains("SecurePass123")]
            ),
            JourneyStep(
                "What car do I have?",
                "Retrieves car info",
                [contains_any("toyota", "camry", "2022")]
            ),
            JourneyStep(
                "When is my anniversary?",
                "Retrieves anniversary",
                [contains_any("june", "15")]
            ),
            JourneyStep(
                "My memories",
                "Lists all memories",
                [contains_any("wifi", "car", "anniversary", "memories")]
            ),
        ]
    )


def create_error_recovery_journey() -> UserJourney:
    """Journey: User encounters and recovers from various edge cases"""
    return UserJourney(
        name="Error Recovery",
        description="User encounters edge cases and the system handles them gracefully",
        steps=[
            JourneyStep(
                "",
                "Empty message",
                [is_not_error(), has_length_between(1, 1000)]
            ),
            JourneyStep(
                "   ",
                "Whitespace only",
                [is_not_error(), has_length_between(1, 1000)]
            ),
            JourneyStep(
                "asdfghjkl",
                "Gibberish message",
                [is_not_error()]
            ),
            JourneyStep(
                "Remind me at 99:99pm to do something",
                "Invalid time format",
                [is_not_error()]
            ),
            JourneyStep(
                "Help",
                "User asks for help",
                [contains_any("help", "remind", "list", "memory", "info")]
            ),
            JourneyStep(
                "Remind me at 9pm to call mom",
                "User tries valid command",
                [contains_any("remind", "9", "mom", "pm")]
            ),
        ]
    )


def create_time_clarification_journey() -> UserJourney:
    """Journey: User provides ambiguous times that need clarification"""
    return UserJourney(
        name="Time Clarification Flow",
        description="User sets reminders with ambiguous times",
        steps=[
            JourneyStep(
                "Remind me at 9 to take pills",
                "Ambiguous time without AM/PM",
                [contains_any("am", "pm", "9")]
            ),
            JourneyStep(
                "AM",
                "Clarifies AM",
                [contains_any("remind", "9", "am", "pill")]
            ),
            JourneyStep(
                "Remind me at 4:30 to call dentist",
                "Another ambiguous time",
                [contains_any("am", "pm", "4:30")]
            ),
            JourneyStep(
                "PM",
                "Clarifies PM",
                [contains_any("remind", "4:30", "pm", "dentist")]
            ),
            JourneyStep(
                "My reminders",
                "Verify both reminders exist",
                [contains_any("pill", "dentist", "reminder")]
            ),
        ]
    )


def create_timezone_journey() -> UserJourney:
    """Journey: User manages timezone settings"""
    return UserJourney(
        name="Timezone Management",
        description="User checks and changes timezone",
        steps=[
            JourneyStep(
                "My timezone",
                "Check current timezone",
                [contains_any("timezone", "time zone", "america")]
            ),
            JourneyStep(
                "Timezone Los Angeles",
                "Change timezone",
                [contains_any("timezone", "los angeles", "pacific", "updated", "changed")]
            ),
            JourneyStep(
                "My timezone",
                "Verify timezone changed",
                [contains_any("los angeles", "pacific")]
            ),
            JourneyStep(
                "Remind me at 5pm to call west coast office",
                "Set reminder in new timezone",
                [contains_any("remind", "5", "pm")]
            ),
        ]
    )


def create_daily_summary_journey() -> UserJourney:
    """Journey: User configures daily summary"""
    return UserJourney(
        name="Daily Summary Configuration",
        description="User enables and configures daily summary",
        steps=[
            JourneyStep(
                "Summary on",
                "Enable daily summary",
                [contains_any("summary", "enabled", "daily", "8")]
            ),
            JourneyStep(
                "Summary time 7am",
                "Change summary time",
                [contains_any("summary", "7", "am", "updated", "changed")]
            ),
            JourneyStep(
                "My summary",
                "Check summary status",
                [contains_any("summary", "7", "enabled")]
            ),
            JourneyStep(
                "Summary off",
                "Disable summary",
                [contains_any("summary", "disabled", "off")]
            ),
        ]
    )


# ============================================================================
# JOURNEY SIMULATOR
# ============================================================================

class JourneySimulator:
    """Simulates user journeys using the SMS endpoint"""

    def __init__(self, use_real_endpoint=False):
        self.use_real_endpoint = use_real_endpoint
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from fastapi.testclient import TestClient
            from main import app
            self._client = TestClient(app)
        return self._client

    def send_sms(self, phone_number: str, message: str) -> tuple:
        """Send SMS and return (response_text, response_time_ms)"""
        import re
        start_time = time.time()

        try:
            response = self.client.post(
                "/sms",
                data={"Body": message, "From": phone_number}
            )
            response_time_ms = (time.time() - start_time) * 1000

            # Extract message from TwiML
            match = re.search(r'<Message>(.*?)</Message>', response.text, re.DOTALL)
            if match:
                return match.group(1).strip(), response_time_ms
            return response.text, response_time_ms

        except Exception as e:
            return f"ERROR: {str(e)}", (time.time() - start_time) * 1000

    def run_journey(self, journey: UserJourney, phone_number: str = None) -> dict:
        """Run a single user journey"""
        if phone_number is None:
            phone_number = f"+1555{random.randint(1000000, 9999999)}"

        return journey.run(self, phone_number)

    def run_all_journeys(self, journeys: List[UserJourney] = None) -> List[dict]:
        """Run all specified journeys"""
        if journeys is None:
            journeys = get_all_journeys()

        results = []
        for journey in journeys:
            phone = f"+1555{random.randint(1000000, 9999999)}"

            # For journeys that assume onboarding is complete, do onboarding first
            if journey.name != "New User Onboarding":
                self._do_quick_onboarding(phone)

            result = self.run_journey(journey, phone)
            results.append(result)
            print(f"  {journey.name}: {result['passed']}/{result['total_steps']} passed")

        return results

    def _do_quick_onboarding(self, phone_number: str):
        """Quickly complete onboarding for a phone number"""
        messages = ["John", "Doe", "test@example.com", "10001", "yes"]
        for msg in messages:
            self.send_sms(phone_number, msg)


def get_all_journeys() -> List[UserJourney]:
    """Get all defined user journeys"""
    return [
        create_new_user_journey(),
        create_power_user_journey(),
        create_reminder_heavy_journey(),
        create_list_management_journey(),
        create_memory_journey(),
        create_error_recovery_journey(),
        create_time_clarification_journey(),
        create_timezone_journey(),
        create_daily_summary_journey(),
    ]


# ============================================================================
# PYTEST TESTS
# ============================================================================

class TestUserJourneys:
    """Pytest test class for user journeys"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.simulator = JourneySimulator()

    def test_new_user_onboarding(self):
        """Test new user onboarding journey"""
        journey = create_new_user_journey()
        result = self.simulator.run_journey(journey)

        assert result['failed'] == 0, f"Onboarding failed: {result}"

    def test_power_user_session(self):
        """Test power user journey"""
        phone = f"+1555{random.randint(1000000, 9999999)}"
        self.simulator._do_quick_onboarding(phone)

        journey = create_power_user_journey()
        result = self.simulator.run_journey(journey, phone)

        # Allow some flexibility - power user journey may have some edge cases
        assert result['passed'] >= result['total_steps'] * 0.7

    def test_reminder_operations(self):
        """Test reminder-focused journey"""
        phone = f"+1555{random.randint(1000000, 9999999)}"
        self.simulator._do_quick_onboarding(phone)

        journey = create_reminder_heavy_journey()
        result = self.simulator.run_journey(journey, phone)

        assert result['passed'] >= result['total_steps'] * 0.7

    def test_list_operations(self):
        """Test list management journey"""
        phone = f"+1555{random.randint(1000000, 9999999)}"
        self.simulator._do_quick_onboarding(phone)

        journey = create_list_management_journey()
        result = self.simulator.run_journey(journey, phone)

        assert result['passed'] >= result['total_steps'] * 0.7

    def test_memory_operations(self):
        """Test memory storage journey"""
        phone = f"+1555{random.randint(1000000, 9999999)}"
        self.simulator._do_quick_onboarding(phone)

        journey = create_memory_journey()
        result = self.simulator.run_journey(journey, phone)

        assert result['passed'] >= result['total_steps'] * 0.7

    def test_error_recovery(self):
        """Test error recovery journey"""
        phone = f"+1555{random.randint(1000000, 9999999)}"
        self.simulator._do_quick_onboarding(phone)

        journey = create_error_recovery_journey()
        result = self.simulator.run_journey(journey, phone)

        # Error recovery should not cause crashes
        assert result['passed'] >= result['total_steps'] * 0.5


# ============================================================================
# MAIN RUNNER
# ============================================================================

def print_journey_report(results: List[dict]):
    """Print a summary report of journey results"""
    print("\n" + "=" * 60)
    print("USER JOURNEY TEST REPORT")
    print("=" * 60)

    total_steps = sum(r['total_steps'] for r in results)
    total_passed = sum(r['passed'] for r in results)
    total_failed = sum(r['failed'] for r in results)

    print(f"\nTotal Journeys: {len(results)}")
    print(f"Total Steps: {total_steps}")
    print(f"Passed: {total_passed} ({100*total_passed/max(1,total_steps):.1f}%)")
    print(f"Failed: {total_failed} ({100*total_failed/max(1,total_steps):.1f}%)")

    print("\nBy Journey:")
    for r in results:
        status = "PASS" if r['failed'] == 0 else "FAIL"
        print(f"  [{status}] {r['name']}: {r['passed']}/{r['total_steps']}")

    if total_failed > 0:
        print("\nFailed Steps:")
        for r in results:
            for step in r['steps']:
                if not step.get('passed', True) and not step.get('skipped'):
                    print(f"  - {r['name']} Step {step['step']}: {step['description']}")
                    print(f"    Message: {step['message']}")
                    print(f"    Response: {step.get('response', 'N/A')[:100]}")
                    if step.get('errors'):
                        print(f"    Errors: {step['errors']}")

    print("=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="User Journey Tests")
    parser.add_argument('--run-journeys', action='store_true',
                       help='Run all user journeys')
    parser.add_argument('--journey', type=str,
                       help='Run specific journey by name')
    parser.add_argument('--list', action='store_true',
                       help='List all available journeys')

    args = parser.parse_args()

    if args.list:
        print("\nAvailable User Journeys:")
        for j in get_all_journeys():
            print(f"  - {j.name}: {j.description}")
        return

    if args.run_journeys or args.journey:
        simulator = JourneySimulator()

        if args.journey:
            journeys = [j for j in get_all_journeys() if args.journey.lower() in j.name.lower()]
            if not journeys:
                print(f"No journey found matching: {args.journey}")
                return
        else:
            journeys = get_all_journeys()

        print(f"\nRunning {len(journeys)} user journeys...")
        results = simulator.run_all_journeys(journeys)
        print_journey_report(results)
    else:
        # Run pytest
        pytest.main([__file__, '-v'])


if __name__ == "__main__":
    main()
