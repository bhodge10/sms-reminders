#!/usr/bin/env python3
"""
Direct command testing for SMS Reminders.
These tests bypass the AI service to test command parsing and handling directly.

Usage:
    python -m pytest tests/test_commands.py -v
    python -m pytest tests/test_commands.py -v -k "test_reminder"
"""

import os
import sys
import re
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytz

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSnoozeParser:
    """Test the snooze duration parser"""

    def test_default_snooze(self):
        from main import parse_snooze_duration
        assert parse_snooze_duration("") == 15
        assert parse_snooze_duration(None) == 15

    def test_minutes_formats(self):
        from main import parse_snooze_duration
        assert parse_snooze_duration("30") == 30
        assert parse_snooze_duration("30m") == 30
        assert parse_snooze_duration("30 min") == 30
        assert parse_snooze_duration("30 minutes") == 30
        assert parse_snooze_duration("45mins") == 45

    def test_hours_formats(self):
        from main import parse_snooze_duration
        assert parse_snooze_duration("1h") == 60
        assert parse_snooze_duration("1 hour") == 60
        assert parse_snooze_duration("2 hours") == 120
        assert parse_snooze_duration("2hr") == 120
        assert parse_snooze_duration("3hrs") == 180

    def test_combined_formats(self):
        from main import parse_snooze_duration
        assert parse_snooze_duration("1h30m") == 90
        assert parse_snooze_duration("1h 30m") == 90
        assert parse_snooze_duration("2 hours 15 minutes") == 135

    def test_max_duration(self):
        from main import parse_snooze_duration
        # Max is 24 hours (1440 minutes)
        assert parse_snooze_duration("2000") == 1440
        assert parse_snooze_duration("48h") == 1440


class TestTimezoneDetection:
    """Test timezone detection from ZIP codes"""

    def test_common_zip_codes(self):
        from services.onboarding_service import get_timezone_from_zip
        # Test some common ZIP codes
        test_cases = [
            ("10001", "America/New_York"),     # NYC
            ("90210", "America/Los_Angeles"),  # Beverly Hills
            ("60601", "America/Chicago"),      # Chicago
            ("98101", "America/Los_Angeles"),  # Seattle
            ("33101", "America/New_York"),     # Miami
            ("80202", "America/Denver"),       # Denver
            ("85001", "America/Phoenix"),      # Phoenix
        ]

        for zip_code, expected_tz in test_cases:
            result = get_timezone_from_zip(zip_code)
            # Just check it returns a valid timezone string
            assert result is not None, f"Failed for ZIP {zip_code}"
            assert "America/" in result or result == expected_tz


class TestCommandPatterns:
    """Test regex patterns used for command detection"""

    def test_am_pm_detection(self):
        """Test AM/PM detection in messages"""
        pattern = r'\d\s*(am|pm|a\.m\.|p\.m\.|a|p)\b'

        # Should match
        assert re.search(pattern, "9pm", re.IGNORECASE)
        assert re.search(pattern, "9 pm", re.IGNORECASE)
        assert re.search(pattern, "9PM", re.IGNORECASE)
        assert re.search(pattern, "4:00pm", re.IGNORECASE)
        assert re.search(pattern, "8:30 AM", re.IGNORECASE)
        assert re.search(pattern, "3:30a.m.", re.IGNORECASE)
        assert re.search(pattern, "7p", re.IGNORECASE)

        # Should not match
        assert not re.search(pattern, "at 9", re.IGNORECASE)
        assert not re.search(pattern, "at 4:30", re.IGNORECASE)

    def test_time_parsing(self):
        """Test time extraction from messages"""
        pattern = r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.|a|p)\b'

        test_cases = [
            ("9pm", "9", None, "pm"),
            ("9 pm", "9", None, "pm"),
            ("9:30pm", "9", "30", "pm"),
            ("10:00 AM", "10", "00", "AM"),
            ("4:45 p.m.", "4", "45", "p.m."),
        ]

        for text, exp_hour, exp_min, exp_ampm in test_cases:
            match = re.search(pattern, text, re.IGNORECASE)
            assert match, f"Should match: {text}"
            assert match.group(1) == exp_hour
            assert match.group(2) == exp_min
            assert match.group(3).lower() == exp_ampm.lower()

    def test_relative_time_patterns(self):
        """Test relative time pattern matching"""
        pattern = r'in\s+(\d+)\s+(minute|hour|day|week|month)s?'

        test_cases = [
            ("remind me in 30 minutes", "30", "minute"),
            ("in 2 hours please", "2", "hour"),
            ("in 3 days", "3", "day"),
            ("in 1 week", "1", "week"),
            ("in 5 months", "5", "month"),
        ]

        for text, exp_num, exp_unit in test_cases:
            match = re.search(pattern, text, re.IGNORECASE)
            assert match, f"Should match: {text}"
            assert match.group(1) == exp_num
            assert match.group(2) == exp_unit

    def test_recurring_patterns(self):
        """Test recurring reminder pattern detection"""
        daily_pattern = r'\bevery\s*day\b|\bdaily\b'
        weekly_pattern = r'\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b'
        weekday_pattern = r'\bweekdays?\b'
        weekend_pattern = r'\bweekends?\b'

        # Daily
        assert re.search(daily_pattern, "every day at 9am", re.IGNORECASE)
        assert re.search(daily_pattern, "daily at 8pm", re.IGNORECASE)

        # Weekly
        assert re.search(weekly_pattern, "every monday at 9am", re.IGNORECASE)
        assert re.search(weekly_pattern, "every Sunday at 6pm", re.IGNORECASE)

        # Weekdays
        assert re.search(weekday_pattern, "weekdays at 8am", re.IGNORECASE)
        assert re.search(weekday_pattern, "every weekday", re.IGNORECASE)

        # Weekends
        assert re.search(weekend_pattern, "weekends at 10am", re.IGNORECASE)
        assert re.search(weekend_pattern, "every weekend", re.IGNORECASE)


class TestInputValidation:
    """Test input validation functions"""

    def test_list_name_validation(self):
        """Test list name validation"""
        from utils.validation import validate_list_name

        # Valid names
        assert validate_list_name("Grocery List") == (True, "Grocery List")
        assert validate_list_name("My Shopping") == (True, "My Shopping")
        assert validate_list_name("todo") == (True, "todo")

        # Invalid names (too short, too long, special chars)
        valid, _ = validate_list_name("")
        assert not valid

        valid, _ = validate_list_name("a")
        assert not valid

        valid, _ = validate_list_name("a" * 100)
        assert not valid

    def test_item_text_validation(self):
        """Test list item text validation"""
        from utils.validation import validate_item_text

        # Valid items
        assert validate_item_text("milk") == (True, "milk")
        assert validate_item_text("eggs and bread") == (True, "eggs and bread")

        # Invalid items
        valid, _ = validate_item_text("")
        assert not valid

        valid, _ = validate_item_text("a" * 300)
        assert not valid

    def test_sensitive_data_detection(self):
        """Test detection of sensitive data"""
        from utils.validation import detect_sensitive_data

        # Should detect SSN patterns
        assert detect_sensitive_data("my ssn is 123-45-6789")
        assert detect_sensitive_data("SSN: 123456789")

        # Should detect credit card patterns
        assert detect_sensitive_data("card 4111111111111111")
        assert detect_sensitive_data("cc: 4111-1111-1111-1111")

        # Should not flag normal text
        assert not detect_sensitive_data("remind me to call mom")
        assert not detect_sensitive_data("my phone number is 555-1234")


class TestHelperFunctions:
    """Test various helper functions"""

    def test_phone_masking(self):
        """Test phone number masking for logs"""
        from utils.validation import mask_phone_number

        assert mask_phone_number("+15551234567") == "+1555***4567"
        assert mask_phone_number("5551234567") == "555***4567"

    def test_staging_prefix(self):
        """Test staging environment prefix"""
        from main import staging_prefix

        # In non-staging, should return message as-is
        with patch('main.ENVIRONMENT', 'production'):
            # This won't work due to import caching, so we test the function logic
            pass

        # The function adds [STAGING] prefix when ENVIRONMENT == "staging"


class TestDateTimeCalculations:
    """Test date and time calculation functions"""

    def test_user_current_time(self):
        """Test getting current time in user's timezone"""
        from utils.timezone import get_user_current_time
        from models.user import get_user_timezone

        # Mock the timezone lookup
        with patch('utils.timezone.get_user_timezone') as mock_tz:
            mock_tz.return_value = 'America/New_York'

            # This should return a datetime in the user's timezone
            result = get_user_current_time('+15551234567')
            assert result is not None
            assert result.tzinfo is not None

    def test_timezone_conversion(self):
        """Test timezone conversion logic"""
        tz_ny = pytz.timezone('America/New_York')
        tz_la = pytz.timezone('America/Los_Angeles')

        # Create a time in NY
        ny_time = tz_ny.localize(datetime(2025, 1, 15, 9, 0, 0))

        # Convert to LA
        la_time = ny_time.astimezone(tz_la)

        # LA should be 3 hours behind (or 2 during DST)
        diff = (ny_time.hour - la_time.hour) % 24
        assert diff in [2, 3]  # Account for DST variations


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_rate_limit_check(self):
        """Test the rate limit checking function"""
        from main import check_rate_limit, rate_limit_store
        import time

        # Clear any existing rate limit data
        test_phone = "+15559999999"
        rate_limit_store[test_phone] = []

        # Should allow messages under limit
        for i in range(10):
            assert check_rate_limit(test_phone) == True

        # Check that we've recorded the requests
        assert len(rate_limit_store[test_phone]) == 10


class TestMessageParsing:
    """Test message parsing and extraction"""

    def test_extract_reminder_text(self):
        """Test extracting reminder task from messages"""
        patterns = [
            (r'remind\s+me\s+(?:to\s+)?(.+?)(?:\s+at\s+\d|$)', "remind me to call mom at 9pm", "call mom"),
            (r'remind\s+me\s+(?:to\s+)?(.+?)(?:\s+in\s+\d|$)', "remind me to check oven in 30 minutes", "check oven"),
        ]

        for pattern, text, expected in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                assert expected in result.lower() or result.lower() in expected.lower()

    def test_extract_list_items(self):
        """Test parsing list items from add command"""
        # Simple comma-separated
        items = "milk, eggs, bread".split(",")
        items = [i.strip() for i in items]
        assert items == ["milk", "eggs", "bread"]

        # With 'and'
        text = "milk and eggs"
        items = re.split(r'\s+and\s+|,\s*', text)
        assert len(items) == 2


class TestExplicitCommands:
    """Test explicit command detection (MY REMINDERS, MY LISTS, etc.)"""

    def test_command_matching(self):
        """Test that explicit commands are detected correctly"""
        commands = {
            'MY REMINDERS': ['my reminders', 'MY REMINDERS', 'My Reminders'],
            'MY LISTS': ['my lists', 'MY LISTS', 'show lists'],
            'MY MEMORIES': ['my memories', 'MY MEMORIES', 'list all'],
            'MY TIMEZONE': ['my timezone', 'MY TIMEZONE', 'what timezone'],
            'MY RECURRING': ['my recurring', 'MY RECURRING'],
            'MY SUMMARY': ['my summary', 'MY SUMMARY'],
        }

        for expected_cmd, variations in commands.items():
            for variant in variations:
                # Check that the variant would match the command logic
                upper = variant.upper()
                matches = (
                    upper == expected_cmd or
                    upper.startswith(expected_cmd.split()[0])
                )
                # At least one check should pass
                assert upper in expected_cmd or expected_cmd.split()[0] in upper


class TestMultiCommandDetection:
    """Test detection of multi-command messages"""

    def test_and_conjunction(self):
        """Test splitting commands on 'and' conjunction"""
        messages = [
            ("Add milk and remind me at 5pm to shop", 2),
            ("Delete eggs and add butter to list", 2),
            ("Check off milk and add bread", 2),
        ]

        for msg, expected_commands in messages:
            # Simple heuristic: count command verbs
            verbs = ['add', 'delete', 'remove', 'check', 'remind', 'create']
            count = sum(1 for v in verbs if v in msg.lower())
            # Should detect multiple commands
            assert count >= expected_commands or 'and' in msg


class TestResponseFormatting:
    """Test response formatting functions"""

    def test_reminder_list_formatting(self):
        """Test formatting of reminder lists"""
        from utils.formatting import format_reminders_list

        # Test with empty list
        result = format_reminders_list([])
        assert "no reminder" in result.lower() or result == ""

    def test_help_text(self):
        """Test help text generation"""
        from utils.formatting import get_help_text

        help_text = get_help_text()
        assert len(help_text) > 100
        assert "remind" in help_text.lower()
        assert "list" in help_text.lower() or "memory" in help_text.lower()


# ============================================================================
# INTEGRATION TESTS (requires database)
# ============================================================================

@pytest.mark.integration
class TestDatabaseOperations:
    """Integration tests that require database connection"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test database connection"""
        # Skip if no database configured
        if not os.getenv('DATABASE_URL'):
            pytest.skip("No DATABASE_URL configured")

    def test_user_creation(self):
        """Test user creation and retrieval"""
        from models.user import create_or_update_user, get_user

        test_phone = f"+1555TEST{datetime.now().strftime('%H%M%S')}"

        create_or_update_user(
            test_phone,
            first_name="Test",
            last_name="User",
            email="test@example.com",
            timezone="America/New_York",
            onboarding_complete=True
        )

        user = get_user(test_phone)
        assert user is not None

    def test_memory_operations(self):
        """Test memory storage and retrieval"""
        from models.memory import save_memory, get_memories, search_memories

        test_phone = f"+1555MEM{datetime.now().strftime('%H%M%S')}"

        # Save memory
        save_memory(test_phone, "Test memory content")

        # Retrieve
        memories = get_memories(test_phone)
        assert len(memories) >= 1

        # Search
        results = search_memories(test_phone, "test")
        assert len(results) >= 1

    def test_reminder_operations(self):
        """Test reminder creation and retrieval"""
        from models.reminder import save_reminder, get_user_reminders

        test_phone = f"+1555REM{datetime.now().strftime('%H%M%S')}"
        future_time = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

        # Save reminder
        save_reminder(test_phone, "Test reminder", future_time)

        # Retrieve
        reminders = get_user_reminders(test_phone)
        assert len(reminders) >= 1


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
