"""
Pytest configuration and fixtures for stress testing
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pytz

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def test_phone_numbers():
    """Generate test phone numbers for stress testing"""
    return [f"+1555000{str(i).zfill(4)}" for i in range(1, 101)]


@pytest.fixture
def mock_twilio():
    """Mock Twilio SMS sending to avoid actual message sending"""
    with patch('services.sms_service.send_sms') as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_openai_responses():
    """
    Provides mock AI responses for different message types.
    This allows testing without hitting the actual OpenAI API.
    """
    return {
        # Memory storage
        "remember": {
            "action": "store",
            "item": "test item",
            "details": "test details",
            "memory_text": "Test memory stored",
            "confirmation": "Got it! I'll remember that."
        },
        # Reminder with specific time
        "remind_at": {
            "action": "reminder",
            "reminder_text": "test task",
            "reminder_date": (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            "confirmation": "I'll remind you at the specified time."
        },
        # Relative reminder
        "remind_in": {
            "action": "reminder_relative",
            "reminder_text": "test task",
            "offset_minutes": 30
        },
        # Recurring reminder
        "remind_every": {
            "action": "reminder_recurring",
            "reminder_text": "daily task",
            "recurrence_type": "daily",
            "recurrence_day": None,
            "time": "09:00"
        },
        # List creation
        "create_list": {
            "action": "create_list",
            "list_name": "Test List",
            "confirmation": "Created your Test List!"
        },
        # Add to list
        "add_to_list": {
            "action": "add_to_list",
            "list_name": "Grocery List",
            "item_text": "milk, eggs, bread",
            "confirmation": "Added items to your Grocery List"
        },
        # Clarify time
        "clarify_time": {
            "action": "clarify_time",
            "reminder_text": "test task",
            "time_mentioned": "9",
            "response": "Got it! Do you mean 9 AM or PM?"
        },
        # Retrieve memory
        "retrieve": {
            "action": "retrieve",
            "query": "test query",
            "response": "Based on your memories..."
        },
        # Help
        "help": {
            "action": "help",
            "response": "Hi! How can I help you today?"
        },
        # Show help
        "show_help": {
            "action": "show_help",
            "response": "Here's how to use the service..."
        },
        # Delete reminder
        "delete_reminder": {
            "action": "delete_reminder",
            "search_term": "test",
            "confirmation": "Deleted your reminder"
        },
        # Delete memory
        "delete_memory": {
            "action": "delete_memory",
            "search_term": "test",
            "confirmation": "Looking for memories about test..."
        },
        # Error fallback
        "error": {
            "action": "error",
            "response": "Sorry, I had trouble understanding that."
        }
    }


@pytest.fixture
def ai_response_matcher(mock_openai_responses):
    """
    Returns a function that matches user input to appropriate mock AI response.
    More sophisticated pattern matching for realistic testing.
    """
    import re

    def match_response(message):
        msg_lower = message.lower().strip()

        # Memory storage patterns
        if any(word in msg_lower for word in ['remember', 'store', 'save that', 'keep track']):
            response = mock_openai_responses["remember"].copy()
            # Extract what to remember
            for pattern in [r'remember\s+(.+)', r'store\s+(.+)', r'save that\s+(.+)']:
                match = re.search(pattern, msg_lower)
                if match:
                    response["memory_text"] = match.group(1)
                    break
            return response

        # Recurring reminders
        if any(phrase in msg_lower for phrase in ['every day', 'every monday', 'every week', 'daily', 'weekly', 'weekdays', 'weekends']):
            response = mock_openai_responses["remind_every"].copy()
            # Determine recurrence type
            if 'weekday' in msg_lower:
                response["recurrence_type"] = "weekdays"
            elif 'weekend' in msg_lower:
                response["recurrence_type"] = "weekends"
            elif 'week' in msg_lower or any(day in msg_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
                response["recurrence_type"] = "weekly"
            return response

        # Relative time reminders
        if re.search(r'in\s+\d+\s+(minute|hour|day|week|month)', msg_lower):
            response = mock_openai_responses["remind_in"].copy()
            match = re.search(r'in\s+(\d+)\s+(minute|hour|day|week|month)', msg_lower)
            if match:
                num = int(match.group(1))
                unit = match.group(2)
                if unit == 'minute':
                    response["offset_minutes"] = num
                elif unit == 'hour':
                    response["offset_minutes"] = num * 60
                elif unit == 'day':
                    response["offset_days"] = num
                elif unit == 'week':
                    response["offset_weeks"] = num
                elif unit == 'month':
                    response["offset_months"] = num
            return response

        # Specific time reminders
        if 'remind' in msg_lower and re.search(r'\d{1,2}(:\d{2})?\s*(am|pm)', msg_lower, re.IGNORECASE):
            response = mock_openai_responses["remind_at"].copy()
            return response

        # Ambiguous time reminders (no AM/PM)
        if 'remind' in msg_lower and re.search(r'at\s+\d{1,2}(:\d{2})?(?!\s*(am|pm))', msg_lower, re.IGNORECASE):
            response = mock_openai_responses["clarify_time"].copy()
            match = re.search(r'at\s+(\d{1,2}(:\d{2})?)', msg_lower)
            if match:
                response["time_mentioned"] = match.group(1)
            return response

        # List creation
        if any(phrase in msg_lower for phrase in ['create a list', 'create list', 'new list', 'start a list']):
            response = mock_openai_responses["create_list"].copy()
            match = re.search(r'(?:create|start|new)\s+(?:a\s+)?(?:list\s+)?(?:called\s+|named\s+)?(.+?)(?:\s+list)?$', msg_lower)
            if match:
                response["list_name"] = match.group(1).title()
            return response

        # Add to list
        if any(phrase in msg_lower for phrase in ['add to', 'add items', 'put on']):
            response = mock_openai_responses["add_to_list"].copy()
            return response

        # Delete reminder
        if any(phrase in msg_lower for phrase in ['delete reminder', 'cancel reminder', 'remove reminder']):
            response = mock_openai_responses["delete_reminder"].copy()
            return response

        # Delete memory
        if any(phrase in msg_lower for phrase in ['delete memory', 'forget', 'remove memory']):
            response = mock_openai_responses["delete_memory"].copy()
            return response

        # Retrieve/query
        if any(word in msg_lower for word in ['what', 'when', 'where', 'who', 'how', 'tell me', 'show me']):
            return mock_openai_responses["retrieve"].copy()

        # Help
        if any(word in msg_lower for word in ['help', 'how do', 'guide', 'info', 'commands', '?']):
            return mock_openai_responses["show_help"].copy()

        # Greetings
        if any(word in msg_lower for word in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']):
            return mock_openai_responses["help"].copy()

        # Default - help response for unclear messages
        return mock_openai_responses["help"].copy()

    return match_response


class MockAIService:
    """
    Mock AI service that returns predictable responses for testing.
    Can be configured to simulate different behaviors.
    """

    def __init__(self, response_matcher):
        self.response_matcher = response_matcher
        self.call_count = 0
        self.calls = []
        self.simulate_errors = False
        self.error_rate = 0.0  # 0.0 to 1.0
        self.latency = 0  # milliseconds

    def process_with_ai(self, message, phone_number, context=None):
        """Mock implementation of process_with_ai"""
        import random
        import time

        self.call_count += 1
        self.calls.append({
            'message': message,
            'phone_number': phone_number,
            'timestamp': datetime.now()
        })

        # Simulate latency
        if self.latency > 0:
            time.sleep(self.latency / 1000)

        # Simulate random errors
        if self.simulate_errors and random.random() < self.error_rate:
            return {
                "action": "error",
                "response": "Sorry, I had trouble processing that. Could you try again?"
            }

        return self.response_matcher(message)


@pytest.fixture
def mock_ai_service(ai_response_matcher):
    """Provides a configured MockAIService instance"""
    return MockAIService(ai_response_matcher)


@pytest.fixture
def app_client():
    """
    Creates a FastAPI test client.
    This allows testing the SMS endpoint without running a server.
    """
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Sample user data for testing onboarding and user operations"""
    return {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "zip_code": "10001",
        "timezone": "America/New_York"
    }


@pytest.fixture
def sample_messages():
    """
    A comprehensive collection of sample messages covering all features.
    Useful for bulk testing and stress testing.
    """
    return {
        # Onboarding
        "onboarding": [
            "John",
            "Doe",
            "john@example.com",
            "90210",
            "yes"
        ],

        # Memory operations
        "memories": [
            "Remember my wifi password is HomeNetwork123",
            "Store that my car is a 2020 Honda Civic",
            "Remember my doctor's number is 555-1234",
            "What's my wifi password?",
            "When did I store my car info?",
            "My memories",
            "Delete memory about wifi"
        ],

        # Reminder operations - specific times
        "reminders_specific": [
            "Remind me at 9pm to take medicine",
            "Remind me tomorrow at 8am to call mom",
            "Remind me on Saturday at 3pm to go shopping",
            "Remind me at 4:30pm to pick up kids",
            "Remind me next Monday at 10am for meeting"
        ],

        # Reminder operations - relative times
        "reminders_relative": [
            "Remind me in 30 minutes to check the oven",
            "Remind me in 2 hours to call back",
            "Remind me in 3 days to follow up",
            "Remind me in 1 week to pay bills",
            "Remind me in 2 months to renew license"
        ],

        # Recurring reminders
        "reminders_recurring": [
            "Remind me every day at 7pm to take medicine",
            "Every Sunday at 6pm remind me to take out garbage",
            "Remind me every weekday at 8am to check email",
            "On weekends at 10am remind me to exercise",
            "Monthly on the 15th at 3pm remind me to pay rent"
        ],

        # Ambiguous reminders (need clarification)
        "reminders_ambiguous": [
            "Remind me at 9 to take medicine",
            "Remind me at 4:30 to call wife",
            "Remind me tomorrow to check email"
        ],

        # List operations
        "lists": [
            "Create a grocery list",
            "Add milk, eggs, bread to grocery list",
            "Add butter to grocery list",
            "Show grocery list",
            "Check off milk",
            "My lists",
            "Delete eggs from grocery list"
        ],

        # Account management
        "account": [
            "My timezone",
            "Timezone Los Angeles",
            "My account",
            "My reminders",
            "My recurring",
            "Summary on",
            "Summary time 7am",
            "My summary"
        ],

        # Help and info
        "help": [
            "Help",
            "?",
            "Info",
            "Guide",
            "Commands",
            "What can you do?"
        ],

        # Greetings
        "greetings": [
            "Hi",
            "Hello",
            "Hey there",
            "Good morning"
        ],

        # Edge cases
        "edge_cases": [
            "",  # Empty message
            "   ",  # Whitespace only
            "a" * 500,  # Very long message
            "Remind me at 25:00pm to do something",  # Invalid time
            "!!!@@@###",  # Special characters
            "Remind me remind me remind me",  # Repetitive
            "1234567890",  # Numbers only
            "Delete delete delete"  # Repetitive command
        ],

        # Multi-command messages
        "multi_command": [
            "Add milk to grocery list and remind me at 5pm to go shopping",
            "Remove eggs and add butter to grocery list",
            "Delete my dentist reminder and set a new one for tomorrow at 9am"
        ],

        # Snooze and management
        "snooze": [
            "Snooze",
            "Snooze 30",
            "Snooze 1h",
            "Snooze 2 hours"
        ],

        # Delete operations
        "delete": [
            "Delete reminder 1",
            "Delete all reminders",
            "Delete all memories",
            "Delete all lists",
            "Cancel"
        ]
    }
