#!/usr/bin/env python
"""
Automated Conversational Tests for Remyndrs SMS Service

Sends test messages to the /sms endpoint and logs all interactions.
"""

import json
import requests
import time
from datetime import datetime, timedelta
import re

# Configuration
API_URL = "http://localhost:8000/sms"
TEST_PHONE = "+15559876548"  # Fresh test phone for full test run

# Get current time context for the log
NOW = datetime.now()
TODAY_STR = NOW.strftime("%Y-%m-%d")
TODAY_WEEKDAY = NOW.strftime("%A")
TOMORROW_WEEKDAY = (NOW + timedelta(days=1)).strftime("%A")


def parse_twiml_response(xml_text):
    """Extract message text from TwiML response."""
    # Simple regex to extract <Message>...</Message> content
    match = re.search(r'<Message>(.*?)</Message>', xml_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return xml_text


def send_message(message):
    """Send a message to the SMS endpoint and return the response."""
    try:
        response = requests.post(
            API_URL,
            data={
                "Body": message,
                "From": TEST_PHONE
            },
            timeout=60
        )
        return {
            "status_code": response.status_code,
            "raw_response": response.text,
            "parsed_response": parse_twiml_response(response.text),
            "error": None
        }
    except requests.exceptions.RequestException as e:
        return {
            "status_code": None,
            "raw_response": None,
            "parsed_response": None,
            "error": str(e)
        }


def generate_onboarding_scenarios():
    """Generate onboarding steps to set up the test user."""
    return [
        {
            "message": "START",
            "category": "onboarding",
            "expected_behavior": "Should trigger welcome message and ask for name"
        },
        {
            "message": "Test User",
            "category": "onboarding",
            "expected_behavior": "Should accept name and ask for email"
        },
        {
            "message": "testuser@example.com",
            "category": "onboarding",
            "expected_behavior": "Should accept email and ask for ZIP code"
        },
        {
            "message": "90210",
            "category": "onboarding",
            "expected_behavior": "Should complete onboarding and confirm timezone"
        },
    ]


def generate_test_scenarios():
    """Generate 20-30 realistic test scenarios."""
    scenarios = [
        # Basic reminders with various time formats
        {
            "message": "Remind me to call mom at 3pm",
            "category": "basic_reminder",
            "expected_behavior": "Should create a reminder for 3pm today or tomorrow"
        },
        {
            "message": "remind me tomorrow at 10am to take my vitamins",
            "category": "basic_reminder",
            "expected_behavior": "Should create a reminder for tomorrow at 10:00 AM"
        },
        {
            "message": "Reminder: pick up dry cleaning at 5:30pm",
            "category": "basic_reminder",
            "expected_behavior": "Should create a reminder for 5:30 PM"
        },
        {
            "message": "remind me in 3 hours to check the oven",
            "category": "relative_time",
            "expected_behavior": "Should create a reminder 3 hours from now"
        },
        {
            "message": "remind me in 30 minutes to move the laundry",
            "category": "relative_time",
            "expected_behavior": "Should create a reminder 30 minutes from now"
        },

        # Natural language variations
        {
            "message": "next Tuesday at noon remind me about the dentist appointment",
            "category": "natural_language",
            "expected_behavior": "Should create a reminder for next Tuesday at 12:00 PM"
        },
        {
            "message": "Can you remind me this Friday evening to water the plants?",
            "category": "natural_language",
            "expected_behavior": "Should create a reminder for Friday evening (around 6pm)"
        },
        {
            "message": "set a reminder for the meeting on January 25th at 2pm",
            "category": "natural_language",
            "expected_behavior": "Should create a reminder for January 25th at 2:00 PM"
        },
        {
            "message": "remind me end of day to submit timesheet",
            "category": "natural_language",
            "expected_behavior": "Should create a reminder for end of day (around 5-6pm)"
        },
        {
            "message": "tomorrow morning remind me to call the insurance company",
            "category": "natural_language",
            "expected_behavior": "Should create a reminder for tomorrow morning (around 8-9am)"
        },

        # Edge cases - timezone and same-day
        {
            "message": "remind me at 11:59pm tonight to lock the doors",
            "category": "edge_case",
            "expected_behavior": "Should create a reminder for 11:59 PM tonight"
        },
        {
            "message": "remind me at midnight to wish Sarah happy birthday",
            "category": "edge_case",
            "expected_behavior": "Should create a reminder for 12:00 AM (next occurrence)"
        },
        {
            "message": "remind me December 31st 2026 at 11pm for new years countdown",
            "category": "edge_case",
            "expected_behavior": "Should create a far-future reminder for Dec 31, 2026"
        },
        {
            "message": "remind me in 1 minute to test this",
            "category": "edge_case",
            "expected_behavior": "Should create a reminder 1 minute from now"
        },

        # List management
        {
            "message": "create a grocery list",
            "category": "list_management",
            "expected_behavior": "Should create a new list called 'grocery'"
        },
        {
            "message": "add milk, eggs, and bread to my grocery list",
            "category": "list_management",
            "expected_behavior": "Should add 3 items to the grocery list"
        },
        {
            "message": "what's on my grocery list?",
            "category": "list_management",
            "expected_behavior": "Should display items on the grocery list"
        },
        {
            "message": "add butter to groceries",
            "category": "list_management",
            "expected_behavior": "Should add butter to the grocery list"
        },
        {
            "message": "mark milk as done on grocery list",
            "category": "list_management",
            "expected_behavior": "Should mark milk as completed"
        },
        {
            "message": "show all my lists",
            "category": "list_management",
            "expected_behavior": "Should display all user lists"
        },

        # Reminder management
        {
            "message": "what reminders do I have?",
            "category": "reminder_management",
            "expected_behavior": "Should list all pending reminders"
        },
        {
            "message": "show my upcoming reminders",
            "category": "reminder_management",
            "expected_behavior": "Should list pending reminders"
        },
        {
            "message": "delete my reminder about vitamins",
            "category": "reminder_management",
            "expected_behavior": "Should delete the vitamins reminder"
        },
        {
            "message": "snooze the dentist reminder for 1 hour",
            "category": "reminder_management",
            "expected_behavior": "Should snooze/reschedule the dentist reminder"
        },

        # Memory storage
        {
            "message": "remember that my wifi password is BlueHouse2024",
            "category": "memory",
            "expected_behavior": "Should store this as a memory"
        },
        {
            "message": "what's my wifi password?",
            "category": "memory",
            "expected_behavior": "Should recall the wifi password memory"
        },
        {
            "message": "remember Sarah's birthday is March 15",
            "category": "memory",
            "expected_behavior": "Should store Sarah's birthday"
        },

        # Complex multi-item
        {
            "message": "create a todo list for today: call dentist, buy groceries, pick up package, reply to emails",
            "category": "complex",
            "expected_behavior": "Should create a list with 4 items"
        },
        {
            "message": "remind me every day at 8am to take medication",
            "category": "recurring",
            "expected_behavior": "Should create a daily recurring reminder"
        },
        {
            "message": "remind me every Monday at 9am about team standup",
            "category": "recurring",
            "expected_behavior": "Should create a weekly recurring reminder"
        },

        # Help and info
        {
            "message": "help",
            "category": "info",
            "expected_behavior": "Should display help text"
        },
        {
            "message": "what can you do?",
            "category": "info",
            "expected_behavior": "Should explain capabilities"
        },
    ]
    return scenarios


def run_tests():
    """Run all test scenarios and log results."""
    onboarding = generate_onboarding_scenarios()
    scenarios = generate_test_scenarios()
    all_scenarios = onboarding + scenarios
    results = []

    print(f"Starting conversation tests at {NOW.isoformat()}")
    print(f"API URL: {API_URL}")
    print(f"Test Phone: {TEST_PHONE}")
    print(f"Today is {TODAY_WEEKDAY}, {TODAY_STR}")
    print(f"Tomorrow is {TOMORROW_WEEKDAY}")
    print("-" * 60)

    print("\n=== PHASE 1: ONBOARDING ===")
    for i, scenario in enumerate(onboarding, 1):
        print(f"\n[Onboarding {i}/{len(onboarding)}] {scenario['message'][:50]}...")

        timestamp = datetime.now().isoformat()
        response = send_message(scenario["message"])

        result = {
            "test_number": f"onboarding_{i}",
            "timestamp": timestamp,
            "user_message": scenario["message"],
            "category": scenario["category"],
            "expected_behavior": scenario["expected_behavior"],
            "status_code": response["status_code"],
            "system_response": response["parsed_response"],
            "raw_response": response["raw_response"],
            "error": response["error"]
        }
        results.append(result)

        if response["error"]:
            print(f"   ERROR: {response['error']}")
        else:
            preview = response["parsed_response"][:100] if response["parsed_response"] else "No response"
            preview_safe = preview.encode('ascii', 'replace').decode('ascii')
            print(f"   Response: {preview_safe}...")

        time.sleep(2)  # Longer delay for onboarding steps

    print("\n=== PHASE 2: FEATURE TESTS ===")
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[{i}/{len(scenarios)}] Testing: {scenario['message'][:50]}...")

        timestamp = datetime.now().isoformat()
        response = send_message(scenario["message"])

        result = {
            "test_number": i,
            "timestamp": timestamp,
            "user_message": scenario["message"],
            "category": scenario["category"],
            "expected_behavior": scenario["expected_behavior"],
            "status_code": response["status_code"],
            "system_response": response["parsed_response"],
            "raw_response": response["raw_response"],
            "error": response["error"]
        }
        results.append(result)

        if response["error"]:
            print(f"   ERROR: {response['error']}")
        else:
            # Show first 100 chars of response (strip emojis for Windows console)
            preview = response["parsed_response"][:100] if response["parsed_response"] else "No response"
            # Remove non-ASCII chars for console output
            preview_safe = preview.encode('ascii', 'replace').decode('ascii')
            print(f"   Response: {preview_safe}...")

        # Small delay between requests to avoid overwhelming the server
        time.sleep(1)

    # Create the final log structure
    test_log = {
        "test_run_metadata": {
            "run_timestamp": NOW.isoformat(),
            "api_url": API_URL,
            "test_phone": TEST_PHONE,
            "today_date": TODAY_STR,
            "today_weekday": TODAY_WEEKDAY,
            "tomorrow_weekday": TOMORROW_WEEKDAY,
            "onboarding_tests": len(onboarding),
            "feature_tests": len(scenarios),
            "total_tests": len(results),
            "note": "This log captures raw responses without evaluating correctness. 'tomorrow' means " + TOMORROW_WEEKDAY + " " + (NOW + timedelta(days=1)).strftime("%Y-%m-%d")
        },
        "test_results": results
    }

    # Write to JSON file
    output_file = "conversation_test_log.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(test_log, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"Tests completed! Results saved to {output_file}")
    print(f"Total tests run: {len(results)}")
    errors = sum(1 for r in results if r["error"])
    if errors:
        print(f"Errors encountered: {errors}")

    return test_log


if __name__ == "__main__":
    run_tests()
