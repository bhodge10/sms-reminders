"""
Conversation Flow Tests - Tests realistic multi-turn conversations with state.

These tests simulate real user interactions by:
1. Setting up user state in the database
2. Processing messages through the AI service
3. Verifying responses and state changes
4. Testing multi-turn conversation flows

This provides much more accurate testing than single-message AI accuracy tests.

Run with: test tests/test_conversation_flows.py -v
"""

import pytest
import json
import re
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytz

# Mark all tests in this module
pytestmark = [pytest.mark.slow, pytest.mark.conversation_flow]


def process_message_flow(phone_number, message):
    """
    Process a message through the AI service and return the action result.
    This simulates what happens when a user sends a message.
    """
    from services.ai_service import process_with_ai
    return process_with_ai(message, phone_number, context={})


def simulate_conversation_turn(phone_number, message):
    """
    Simulate a full conversation turn: message in -> AI processing -> response.
    Returns (action, response_text, full_result)
    """
    result = process_message_flow(phone_number, message)
    action = result.get("action", "unknown")

    # Get response text based on action type
    response = result.get("response") or result.get("confirmation") or ""

    return action, response, result


class ConversationFlowTest:
    """Base class for conversation flow tests."""

    @pytest.fixture(autouse=True)
    def setup(self, onboarded_user, sms_capture):
        """Setup test user and SMS capture."""
        self.phone = onboarded_user["phone"]
        self.sms_capture = sms_capture
        self.user_tz = "America/New_York"

    def send_message(self, message):
        """Send a message and get the AI's interpreted action and response."""
        action, response, full_result = simulate_conversation_turn(self.phone, message)
        self.last_action = action
        self.last_result = full_result
        return response or f"[Action: {action}]"

    def get_last_action(self):
        """Get the last action that was taken."""
        return getattr(self, 'last_action', None)

    def get_last_result(self):
        """Get the full result from the last message."""
        return getattr(self, 'last_result', None)

    def get_user_state(self):
        """Get current user state from database."""
        from models.user import get_user
        return get_user(self.phone)

    def set_user_state(self, **kwargs):
        """Set user state in database."""
        from models.user import create_or_update_user
        create_or_update_user(self.phone, **kwargs)


class TestReminderConversationFlows(ConversationFlowTest):
    """Test multi-turn reminder conversations."""

    def test_reminder_with_time_clarification(self):
        """
        Flow: User sets reminder without AM/PM -> System asks -> User clarifies -> Reminder set
        """
        # Step 1: User sends reminder without AM/PM
        reply = self.send_message("remind me at 4 to call mom")

        # Should ask for AM/PM clarification
        assert "AM" in reply.upper() or "PM" in reply.upper(), f"Expected AM/PM clarification, got: {reply}"

        # Step 2: User clarifies with PM
        reply = self.send_message("PM")

        # Should confirm reminder
        assert "remind" in reply.lower() or "I'll" in reply.lower(), f"Expected reminder confirmation, got: {reply}"
        assert "4" in reply or "4:00" in reply, f"Expected time in confirmation, got: {reply}"

    def test_reminder_with_date_clarification(self):
        """
        Flow: User sets reminder with date but no time -> System asks -> User provides time
        """
        # Step 1: User sends reminder with date but no time
        reply = self.send_message("remind me tomorrow to check email")

        # Should ask for time
        assert "time" in reply.lower() or "when" in reply.lower(), f"Expected time question, got: {reply}"

        # Step 2: User provides time
        reply = self.send_message("9am")

        # Should confirm reminder
        assert "remind" in reply.lower() or "I'll" in reply.lower(), f"Expected confirmation, got: {reply}"
        assert "9" in reply, f"Expected time in confirmation, got: {reply}"

    def test_reminder_complete_in_one_message(self):
        """
        Flow: User provides complete reminder -> Immediate confirmation
        """
        reply = self.send_message("remind me tomorrow at 3pm to take medicine")

        # Should immediately confirm
        assert "remind" in reply.lower() or "I'll" in reply.lower(), f"Expected confirmation, got: {reply}"
        assert "3" in reply or "3:00" in reply, f"Expected time in confirmation, got: {reply}"
        assert "medicine" in reply.lower(), f"Expected task in confirmation, got: {reply}"

    def test_relative_time_reminder(self):
        """
        Flow: User sets reminder with relative time -> Immediate confirmation
        """
        reply = self.send_message("remind me in 30 minutes to check the oven")

        # Should immediately confirm with calculated time
        assert "remind" in reply.lower() or "I'll" in reply.lower() or "got it" in reply.lower(), \
            f"Expected confirmation, got: {reply}"


class TestListConversationFlows(ConversationFlowTest):
    """Test multi-turn list management conversations."""

    def test_create_list_and_add_items(self):
        """
        Flow: User creates list -> Adds items -> Views list
        """
        # Step 1: Create a list
        reply = self.send_message("create a grocery list")
        assert "created" in reply.lower() or "grocery" in reply.lower(), \
            f"Expected list creation confirmation, got: {reply}"

        # Step 2: Add items
        reply = self.send_message("add milk and eggs to grocery list")
        assert "added" in reply.lower(), f"Expected add confirmation, got: {reply}"

        # Step 3: View list
        reply = self.send_message("show grocery list")
        assert "milk" in reply.lower() or "eggs" in reply.lower(), \
            f"Expected list items, got: {reply}"

    def test_add_item_without_list_name(self):
        """
        Flow: User has lists -> Adds item without specifying -> System asks which list
        """
        # First create two lists
        self.send_message("create a grocery list")
        self.send_message("create a todo list")

        # Try to add without specifying list
        reply = self.send_message("add bread")

        # Should ask which list
        assert "which" in reply.lower() or "list" in reply.lower(), \
            f"Expected list selection question, got: {reply}"

    def test_show_current_list(self):
        """
        Flow: User creates list -> Adds items -> Says "show list" -> Shows last active
        """
        # Create and add to list
        self.send_message("create a shopping list")
        self.send_message("add batteries to shopping list")

        # Ask to show list (singular - should show last active)
        reply = self.send_message("show list")

        # Should show shopping list
        assert "batteries" in reply.lower() or "shopping" in reply.lower(), \
            f"Expected shopping list contents, got: {reply}"

    def test_duplicate_list_handling(self):
        """
        Flow: User creates list -> Tries to create same name -> System asks
        """
        # Create first list
        self.send_message("create a grocery list")

        # Try to create duplicate
        reply = self.send_message("create a grocery list")

        # Should mention it exists or ask what to do
        assert "already" in reply.lower() or "exist" in reply.lower() or "have" in reply.lower(), \
            f"Expected duplicate warning, got: {reply}"


class TestDeleteConversationFlows(ConversationFlowTest):
    """Test multi-turn delete conversations."""

    def test_delete_reminder_by_keyword(self):
        """
        Flow: User sets reminder -> Asks to delete by keyword -> Confirms deletion
        """
        # Set a reminder
        self.send_message("remind me tomorrow at 9am to call the dentist")

        # Delete by keyword
        reply = self.send_message("delete my dentist reminder")

        # Should confirm deletion or ask for confirmation
        assert "deleted" in reply.lower() or "dentist" in reply.lower(), \
            f"Expected delete confirmation, got: {reply}"

    def test_delete_with_multiple_matches(self):
        """
        Flow: User has multiple similar reminders -> Asks to delete -> System lists options
        """
        # Set multiple reminders
        self.send_message("remind me tomorrow at 9am to call mom")
        self.send_message("remind me tomorrow at 2pm to call dad")

        # Try to delete "call"
        reply = self.send_message("delete my call reminder")

        # Should list options or ask for clarification
        assert "1" in reply or "which" in reply.lower() or "found" in reply.lower(), \
            f"Expected multiple options or clarification, got: {reply}"

    def test_delete_by_number_selection(self):
        """
        Flow: User deletes -> System shows options -> User selects by number
        """
        # Set reminders
        self.send_message("remind me tomorrow at 9am to task one")
        self.send_message("remind me tomorrow at 2pm to task two")

        # Try to delete ambiguously
        reply = self.send_message("delete reminder")

        if "1" in reply and "2" in reply:
            # System listed options, select one
            reply = self.send_message("1")
            assert "deleted" in reply.lower() or "task" in reply.lower(), \
                f"Expected deletion confirmation, got: {reply}"


class TestSnoozeConversationFlow(ConversationFlowTest):
    """Test snooze functionality which requires recent reminder context."""

    def test_snooze_needs_recent_reminder(self):
        """
        Flow: User says snooze without recent reminder -> System explains
        """
        reply = self.send_message("snooze")

        # Should explain no reminder to snooze or offer help
        assert "no reminder" in reply.lower() or "snooze" in reply.lower() or "help" in reply.lower(), \
            f"Expected snooze context explanation, got: {reply}"


class TestMemoryConversationFlows(ConversationFlowTest):
    """Test memory storage and retrieval conversations."""

    def test_store_and_retrieve_memory(self):
        """
        Flow: User stores info -> Retrieves it later
        """
        # Store memory
        reply = self.send_message("remember my wifi password is ABC123")
        assert "remember" in reply.lower() or "stored" in reply.lower() or "got it" in reply.lower(), \
            f"Expected storage confirmation, got: {reply}"

        # Retrieve memory
        reply = self.send_message("what is my wifi password")
        assert "ABC123" in reply or "wifi" in reply.lower(), \
            f"Expected password in response, got: {reply}"

    def test_delete_memory(self):
        """
        Flow: User stores info -> Deletes it -> Can't retrieve
        """
        # Store
        self.send_message("remember my locker code is 1234")

        # Delete
        reply = self.send_message("forget my locker code")
        assert "deleted" in reply.lower() or "forgot" in reply.lower() or "locker" in reply.lower(), \
            f"Expected delete confirmation, got: {reply}"


class TestEdgeCaseFlows(ConversationFlowTest):
    """Test edge cases that caused production issues."""

    def test_yes_without_context(self):
        """
        Production issue: "Yes" alone should offer help, not confirm random action
        """
        reply = self.send_message("Yes")

        # Should offer help, not confirm anything
        assert "help" in reply.lower() or "can I" in reply.lower() or "?" in reply, \
            f"Expected help offer, got: {reply}"

    def test_number_without_context(self):
        """
        Production issue: "1" or "2" alone needs context to be meaningful
        """
        reply = self.send_message("1")

        # Should ask for clarification or offer help
        assert "help" in reply.lower() or "what" in reply.lower() or "?" in reply, \
            f"Expected clarification request, got: {reply}"

    def test_typo_handling(self):
        """
        Test that common typos still work
        """
        # "remid" instead of "remind"
        reply = self.send_message("remid me tomorrow at 3pm to call mom")

        # Should still understand and confirm or ask for clarification
        assert "remind" in reply.lower() or "call mom" in reply.lower() or "3" in reply, \
            f"Expected reminder handling despite typo, got: {reply}"

    def test_shorthand_handling(self):
        """
        Test that shorthand/abbreviated messages work
        """
        reply = self.send_message("tmrw 3pm dentist")

        # Should understand as a reminder
        assert "remind" in reply.lower() or "dentist" in reply.lower() or "3" in reply, \
            f"Expected reminder from shorthand, got: {reply}"


class TestFullUserJourneys(ConversationFlowTest):
    """Test complete user journeys through multiple features."""

    def test_new_user_sets_reminder_journey(self):
        """
        Journey: New user -> Sets reminder without time -> Clarifies -> Gets confirmation
        """
        # Step 1: Greeting
        reply = self.send_message("hello")
        assert reply is not None, "Expected greeting response"

        # Step 2: Set reminder without full info
        reply = self.send_message("remind me tomorrow to buy groceries")
        assert "time" in reply.lower() or "when" in reply.lower(), \
            f"Expected time question, got: {reply}"

        # Step 3: Provide time
        reply = self.send_message("10am")
        assert "groceries" in reply.lower() or "remind" in reply.lower(), \
            f"Expected reminder confirmation, got: {reply}"

    def test_list_management_journey(self):
        """
        Journey: Create list -> Add items -> Check off -> Show completed
        """
        # Create list
        self.send_message("create a todo list")

        # Add items
        self.send_message("add buy milk to todo list")
        self.send_message("add call mom to todo list")

        # Check off an item
        reply = self.send_message("check off buy milk")
        assert "check" in reply.lower() or "milk" in reply.lower(), \
            f"Expected check off confirmation, got: {reply}"

        # View list
        reply = self.send_message("show todo list")
        assert "milk" in reply.lower() or "mom" in reply.lower(), \
            f"Expected list contents, got: {reply}"

    def test_mixed_feature_journey(self):
        """
        Journey: Store memory -> Set reminder -> Ask about memory -> List reminders
        """
        # Store memory
        self.send_message("remember john's birthday is march 15")

        # Set reminder
        self.send_message("remind me march 14 at 9am to buy birthday gift")

        # Ask about memory
        reply = self.send_message("when is john's birthday")
        assert "march" in reply.lower() or "15" in reply, \
            f"Expected birthday info, got: {reply}"

        # List reminders
        reply = self.send_message("show my reminders")
        assert "birthday" in reply.lower() or "gift" in reply.lower() or "no reminders" in reply.lower(), \
            f"Expected reminder list, got: {reply}"


class TestConversationFlowReport:
    """Generate a summary report of conversation flow test results."""

    @pytest.fixture(autouse=True)
    def setup(self, onboarded_user, sms_capture):
        """Setup for report generation."""
        self.phone = onboarded_user["phone"]
        self.sms_capture = sms_capture
        self.results = []

    @pytest.mark.slow
    def test_generate_flow_report(self, capsys):
        """Run all conversation scenarios and generate report."""

        def send(msg):
            """Send message and return response text."""
            action, response, result = simulate_conversation_turn(self.phone, msg)
            # Return both response and some context about the action
            return f"{response} [action:{action}]" if response else f"[action:{action}]"

        scenarios = [
            # (name, messages, expected_keywords_in_final_response)
            ("Reminder with time clarification",
             ["remind me at 4 to call mom", "PM"],
             ["remind", "4"]),

            ("Reminder with date clarification",
             ["remind me tomorrow to check email", "9am"],
             ["remind", "9"]),

            ("Complete reminder in one message",
             ["remind me tomorrow at 3pm to take medicine"],
             ["remind", "medicine"]),

            ("Create and use list",
             ["create a test list", "add item1 to test list", "show test list"],
             ["item1"]),

            ("Store and retrieve memory",
             ["remember test password is XYZ789", "what is my test password"],
             ["XYZ789"]),
        ]

        print("\n" + "=" * 60)
        print("CONVERSATION FLOW TEST REPORT")
        print("=" * 60)

        passed = 0
        failed = 0

        for name, messages, expected_keywords in scenarios:
            try:
                last_reply = None
                for msg in messages:
                    last_reply = send(msg)

                # Check if expected keywords are in final response
                success = any(kw.lower() in (last_reply or "").lower() for kw in expected_keywords)

                if success:
                    passed += 1
                    status = "[PASS]"
                else:
                    failed += 1
                    status = "[FAIL]"
                    print(f"\n{status}: {name}")
                    print(f"  Messages: {messages}")
                    print(f"  Expected keywords: {expected_keywords}")
                    print(f"  Got: {last_reply}")

                self.results.append({
                    "name": name,
                    "passed": success,
                    "response": last_reply
                })

            except Exception as e:
                failed += 1
                print(f"\n[ERROR]: {name}")
                print(f"  Error: {str(e)}")

        total = passed + failed
        accuracy = (passed / total * 100) if total > 0 else 0

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total scenarios: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success rate: {accuracy:.1f}%")
        print("=" * 60)

        # This should pass if most scenarios work
        assert accuracy >= 60, f"Conversation flow success rate below threshold: {accuracy:.1f}%"
