"""
AI Accuracy Tests - Tests actual AI interpretation of user messages.

These tests call the real OpenAI API to verify the AI correctly interprets
various phrasings, edge cases, and potentially confusing messages.

Run with: test tests/test_ai_accuracy.py -v
Run specific category: test tests/test_ai_accuracy.py -v -k "reminder"

NOTE: These tests use real API calls and will incur OpenAI costs.
      They are marked as 'slow' and skipped by default in quick runs.
"""

import pytest
from datetime import datetime, timedelta

# Skip all tests in this module if OpenAI key is not configured
pytestmark = [pytest.mark.slow, pytest.mark.ai_accuracy]


class AIAccuracyTestCase:
    """Represents a single AI accuracy test case."""

    def __init__(self, message, expected_action, description,
                 expected_fields=None, tags=None):
        self.message = message
        self.expected_action = expected_action
        self.description = description
        self.expected_fields = expected_fields or {}
        self.tags = tags or []


# ============================================================
# TEST CASES - Add new cases here as you discover edge cases
# ============================================================

REMINDER_TEST_CASES = [
    # Basic reminders
    AIAccuracyTestCase(
        "remind me tomorrow at 2pm to call mom",
        "reminder",
        "Basic reminder with specific time",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "remind me to call mom tomorrow at 2pm",
        "reminder",
        "Reminder with reordered words",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "remind me in 30 minutes to check the oven",
        "reminder_relative",
        "Relative time reminder",
        tags=["relative"]
    ),
    AIAccuracyTestCase(
        "remind me in an hour to take medicine",
        "reminder_relative",
        "Relative time with 'an hour'",
        tags=["relative"]
    ),

    # Typos and misspellings
    AIAccuracyTestCase(
        "remid me tomorrow at 3pm to call doctor",
        "reminder",
        "Typo: 'remid' instead of 'remind'",
        tags=["typo"]
    ),
    AIAccuracyTestCase(
        "rmeind me tmrw 2pm call mom",
        "reminder",
        "Multiple typos and shorthand",
        tags=["typo", "shorthand"]
    ),
    AIAccuracyTestCase(
        "remind me tomorow at 5pm dinner",
        "reminder",
        "Typo: 'tomorow'",
        tags=["typo"]
    ),

    # Shorthand and informal
    AIAccuracyTestCase(
        "2pm tomorrow call mom",
        "reminder",
        "Shorthand without 'remind me'",
        tags=["shorthand"]
    ),
    AIAccuracyTestCase(
        "tmrw 3pm dentist",
        "reminder",
        "Very terse shorthand",
        tags=["shorthand"]
    ),
    AIAccuracyTestCase(
        "reminder: call bank at 10am",
        "reminder",
        "Using 'reminder:' prefix",
        tags=["shorthand"]
    ),

    # Recurring reminders
    AIAccuracyTestCase(
        "remind me every day at 9am to take vitamins",
        "reminder_recurring",
        "Daily recurring reminder",
        tags=["recurring"]
    ),
    AIAccuracyTestCase(
        "remind me every monday at 10am about team meeting",
        "reminder_recurring",
        "Weekly recurring reminder",
        tags=["recurring"]
    ),
    AIAccuracyTestCase(
        "remind me on weekdays at 8am to check email",
        "reminder_recurring",
        "Weekday recurring reminder",
        tags=["recurring"]
    ),
    AIAccuracyTestCase(
        "every morning at 7am remind me to exercise",
        "reminder_recurring",
        "Recurring with different word order",
        tags=["recurring"]
    ),

    # Ambiguous time (should trigger clarify_time)
    AIAccuracyTestCase(
        "remind me at 4 to take medicine",
        "clarify_time",
        "Ambiguous time without AM/PM",
        tags=["ambiguous"]
    ),
    AIAccuracyTestCase(
        "remind me at 7 to call john",
        "clarify_time",
        "Ambiguous 7 (could be AM or PM)",
        tags=["ambiguous"]
    ),

    # Edge cases - remind vs remember confusion
    AIAccuracyTestCase(
        "remind me to remember to buy milk",
        "reminder",
        "Uses 'remind' and 'remember' - AI treats as reminder",
        tags=["edge_case", "confusing"]
    ),
    AIAccuracyTestCase(
        "don't let me forget to call at 3pm",
        "reminder",
        "Negative phrasing for reminder",
        tags=["edge_case"]
    ),

    # ============================================================
    # REAL USER ISSUES - From production logs analysis
    # ============================================================

    # Issue: "Remind to" without "me" - missing reminder text
    AIAccuracyTestCase(
        "Remind to call mom tomorrow at 2:00 pm",
        "reminder",
        "PROD BUG: 'Remind to' without 'me' - should still parse reminder",
        tags=["production_bug", "edge_case"]
    ),

    # Issue: Relative date without context
    AIAccuracyTestCase(
        "Remind me 2 days before",
        "clarify_date_time",
        "PROD: Incomplete reminder - should ask what to remind about",
        tags=["production_bug", "ambiguous"]
    ),

    # Issue: "Also remind me" - follow-up reminder (needs context)
    AIAccuracyTestCase(
        "Also remind me 2 days before",
        "help",
        "PROD: Follow-up reminder - AI offers help without context",
        tags=["production_bug", "context_needed"]
    ),

    # Issue: "Start" as first message
    AIAccuracyTestCase(
        "Start",
        "help",
        "PROD: User says 'Start' - should offer help",
        tags=["production_bug", "chitchat"]
    ),

    # Issue: Relative time "in 1 minute"
    AIAccuracyTestCase(
        "Remind me in 1 minute to text",
        "reminder_relative",
        "PROD BUG: Very short relative time should work",
        tags=["production_bug", "relative"]
    ),

    # Issue: Snooze with custom duration - needs context to work
    AIAccuracyTestCase(
        "Snooze 3 minutes",
        "help",
        "PROD: 'Snooze X minutes' - AI offers help without reminder context",
        tags=["production_bug", "context_needed"]
    ),

    # Issue: Update reminder with new time - needs context
    AIAccuracyTestCase(
        "Change my test reminder to 9:00a",
        "help",
        "PROD: Update reminder - AI needs reminder context",
        tags=["production_bug", "context_needed"]
    ),
]

MEMORY_TEST_CASES = [
    # Basic storage
    AIAccuracyTestCase(
        "remember my wifi password is ABC123",
        "store",
        "Basic memory storage",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "remember that john's birthday is march 15",
        "store",
        "Memory with 'remember that'",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "store my license plate ABC-1234",
        "store",
        "Using 'store' keyword",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "save my gym locker code 4521",
        "store",
        "Using 'save' keyword",
        tags=["basic"]
    ),

    # Retrieval - AI may return 'retrieve' or 'help' depending on context
    AIAccuracyTestCase(
        "what did I store about wifi",
        "retrieve",
        "Retrieval question with 'store' reference",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "what is john's birthday",
        "retrieve",
        "Retrieval with full 'what is'",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "do you remember my license plate",
        "retrieve",
        "Retrieval phrased as question",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "show me my memories about locker",
        "retrieve",
        "Explicit memory retrieval",
        tags=["basic"]
    ),

    # Edge cases - these are genuinely confusing
    AIAccuracyTestCase(
        "can you store a reminder for tomorrow",
        "clarify_date_time",
        "Uses 'store' but means reminder - AI asks for time",
        tags=["edge_case", "confusing"]
    ),
    AIAccuracyTestCase(
        "remember to call mom tomorrow at 3pm",
        "reminder",
        "'Remember to' with time should be reminder",
        tags=["edge_case", "confusing"]
    ),
]

LIST_TEST_CASES = [
    # List creation
    AIAccuracyTestCase(
        "create a grocery list",
        "create_list",
        "Basic list creation",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "start a new shopping list",
        "create_list",
        "List creation with 'start'",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "make a todo list",
        "create_list",
        "List creation with 'make'",
        tags=["basic"]
    ),

    # Adding items - AI returns specific action types
    AIAccuracyTestCase(
        "add milk to my grocery list",
        "add_to_list",
        "Add single item to specific list",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "add milk, eggs, and bread",
        "add_item_ask_list",
        "Add multiple items without specifying list",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "add milk eggs bread to grocery",
        "add_to_list",
        "Add multiple items to specific list",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "put batteries on my shopping list",
        "add_to_list",
        "Using 'put' instead of 'add'",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "add to grocery list: milk, eggs, butter",
        "add_to_list",
        "Colon syntax with list name",
        tags=["shorthand"]
    ),

    # ============================================================
    # REAL USER ISSUES - From production logs analysis
    # ============================================================

    # Issue: Multi-item add with "and" - only added first item
    AIAccuracyTestCase(
        "Add milk and eggs",
        "add_item_ask_list",
        "PROD BUG: Multi-item with 'and' - should add BOTH items",
        tags=["production_bug", "multi_item"]
    ),

    # Issue: Complex multi-item add - only added first
    AIAccuracyTestCase(
        "Add peanut butter and jelly, milk, bread to grocery",
        "add_to_list",
        "PROD BUG: Multi-item with commas - should add ALL items",
        tags=["production_bug", "multi_item"]
    ),

    # Issue: Multi-item with commas and "and"
    AIAccuracyTestCase(
        "Add chips and salsa, Mac and cheese to grocery list",
        "add_to_list",
        "PROD BUG: Items containing 'and' with comma separator",
        tags=["production_bug", "multi_item"]
    ),

    # Issue: Show list ambiguity - AI shows current list
    AIAccuracyTestCase(
        "Show list",
        "show_current_list",
        "PROD: Show list - AI shows most recent/current list",
        tags=["production_bug"]
    ),

    # Issue: Show lists (plural)
    AIAccuracyTestCase(
        "Show lists",
        "show_all_lists",
        "PROD: Show all lists",
        tags=["production_bug"]
    ),

    # Issue: "New" in response to duplicate warning - needs context
    AIAccuracyTestCase(
        "New",
        "help",
        "PROD: 'New' alone - AI offers help without context",
        tags=["production_bug", "context_needed"]
    ),
]

DELETE_TEST_CASES = [
    # AI returns specific delete types (delete_reminder, delete_memory, etc.)
    AIAccuracyTestCase(
        "delete my reminder about the dentist",
        "delete_reminder",
        "Delete reminder by description",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "remove the wifi password memory",
        "delete_memory",
        "Delete memory using 'remove'",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "forget the wifi password I stored",
        "delete_memory",
        "Delete memory using 'forget' with context",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "cancel my reminder for tomorrow",
        "delete_reminder",
        "Delete reminder using 'cancel'",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "delete item 3 from grocery list",
        "delete_item",
        "Delete specific list item",
        tags=["basic"]
    ),

    # ============================================================
    # REAL USER ISSUES - From production logs analysis
    # ============================================================

    # Issue: Delete with just number - without context, AI tries to help
    AIAccuracyTestCase(
        "Delete 1",
        "delete_memory",
        "PROD: Delete by number only - AI guesses delete type",
        tags=["production_bug", "ambiguous", "context_needed"]
    ),

    # Issue: Delete with just number (different context)
    AIAccuracyTestCase(
        "Delete 2",
        "delete_memory",
        "PROD: Delete by number - AI guesses delete type",
        tags=["production_bug", "ambiguous", "context_needed"]
    ),

    # Issue: Delete reminder without specifying which
    AIAccuracyTestCase(
        "Delete reminder",
        "help",
        "PROD: Generic delete - AI asks for more info",
        tags=["production_bug", "ambiguous"]
    ),

    # Issue: Delete by keyword that doesn't exist
    AIAccuracyTestCase(
        "Delete coffee",
        "help",
        "PROD: Delete by keyword - AI needs more context",
        tags=["production_bug", "ambiguous"]
    ),

    # Issue: "Delete reminders text" - confusing phrasing
    AIAccuracyTestCase(
        "Delete reminders text",
        "help",
        "PROD: Confusing phrasing - AI asks for clarification",
        tags=["production_bug", "confusing"]
    ),

    # Issue: "Yes" confirmation - requires conversation context
    AIAccuracyTestCase(
        "Yes",
        "help",
        "PROD: 'Yes' without context - AI offers help",
        tags=["production_bug", "context_needed"]
    ),
]

CHITCHAT_TEST_CASES = [
    # AI returns 'help' for greetings to be helpful
    AIAccuracyTestCase(
        "hello",
        "help",
        "Simple greeting - AI offers help",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "hi there",
        "help",
        "Casual greeting",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "thanks for the reminder",
        "help",
        "Thank you - AI offers more help",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "what can you do",
        "show_help",
        "Capability question - shows help",
        tags=["basic"]
    ),
    AIAccuracyTestCase(
        "help",
        "show_help",
        "Direct help request",
        tags=["basic"]
    ),

    # ============================================================
    # REAL USER ISSUES - From production logs analysis
    # ============================================================

    # Issue: User frustrated - AI offers help (support requires keywords)
    AIAccuracyTestCase(
        "Reminders not working right",
        "help",
        "PROD: User complaint - AI offers help",
        tags=["production_bug", "support"]
    ),

    # Issue: Reset request - AI offers help without context
    AIAccuracyTestCase(
        "Reset",
        "help",
        "PROD: 'Reset' alone - AI asks what to reset",
        tags=["production_bug", "context_needed"]
    ),

    # Issue: Snooze without recent reminder - AI offers help
    AIAccuracyTestCase(
        "Snooze",
        "help",
        "PROD: 'Snooze' without recent reminder context",
        tags=["production_bug", "context_needed"]
    ),

    # Issue: List reminders
    AIAccuracyTestCase(
        "List reminders",
        "list_reminders",
        "PROD: Show all reminders",
        tags=["production_bug"]
    ),

    # Issue: Show my reminders
    AIAccuracyTestCase(
        "Show my reminders",
        "list_reminders",
        "PROD: Alternative phrasing for list reminders",
        tags=["production_bug"]
    ),
]


class TestAIAccuracy:
    """
    Tests that verify AI correctly interprets user messages.
    These tests call the real OpenAI API.
    """

    @pytest.fixture(autouse=True)
    def setup(self, onboarded_user):
        """Setup test user for AI calls."""
        self.phone = onboarded_user["phone"]
        self.results = []

    def _test_case(self, test_case):
        """Run a single test case and return result."""
        from services.ai_service import process_with_ai

        try:
            result = process_with_ai(
                test_case.message,
                self.phone,
                context={}
            )

            actual_action = result.get("action", "unknown")
            passed = actual_action == test_case.expected_action

            return {
                "message": test_case.message,
                "expected": test_case.expected_action,
                "actual": actual_action,
                "passed": passed,
                "description": test_case.description,
                "tags": test_case.tags,
                "full_response": result
            }
        except Exception as e:
            return {
                "message": test_case.message,
                "expected": test_case.expected_action,
                "actual": "ERROR",
                "passed": False,
                "description": test_case.description,
                "tags": test_case.tags,
                "error": str(e)
            }

    # ============================================================
    # REMINDER TESTS
    # ============================================================

    @pytest.mark.parametrize("test_case", REMINDER_TEST_CASES,
                             ids=[tc.description for tc in REMINDER_TEST_CASES])
    def test_reminder_interpretation(self, test_case):
        """Test AI correctly interprets reminder-related messages."""
        result = self._test_case(test_case)

        assert result["passed"], (
            f"AI misinterpreted: '{result['message']}'\n"
            f"Expected: {result['expected']}, Got: {result['actual']}\n"
            f"Description: {result['description']}\n"
            f"Full response: {result.get('full_response', result.get('error'))}"
        )

    # ============================================================
    # MEMORY TESTS
    # ============================================================

    @pytest.mark.parametrize("test_case", MEMORY_TEST_CASES,
                             ids=[tc.description for tc in MEMORY_TEST_CASES])
    def test_memory_interpretation(self, test_case):
        """Test AI correctly interprets memory-related messages."""
        result = self._test_case(test_case)

        assert result["passed"], (
            f"AI misinterpreted: '{result['message']}'\n"
            f"Expected: {result['expected']}, Got: {result['actual']}\n"
            f"Description: {result['description']}\n"
            f"Full response: {result.get('full_response', result.get('error'))}"
        )

    # ============================================================
    # LIST TESTS
    # ============================================================

    @pytest.mark.parametrize("test_case", LIST_TEST_CASES,
                             ids=[tc.description for tc in LIST_TEST_CASES])
    def test_list_interpretation(self, test_case):
        """Test AI correctly interprets list-related messages."""
        result = self._test_case(test_case)

        assert result["passed"], (
            f"AI misinterpreted: '{result['message']}'\n"
            f"Expected: {result['expected']}, Got: {result['actual']}\n"
            f"Description: {result['description']}\n"
            f"Full response: {result.get('full_response', result.get('error'))}"
        )

    # ============================================================
    # DELETE TESTS
    # ============================================================

    @pytest.mark.parametrize("test_case", DELETE_TEST_CASES,
                             ids=[tc.description for tc in DELETE_TEST_CASES])
    def test_delete_interpretation(self, test_case):
        """Test AI correctly interprets delete-related messages."""
        result = self._test_case(test_case)

        assert result["passed"], (
            f"AI misinterpreted: '{result['message']}'\n"
            f"Expected: {result['expected']}, Got: {result['actual']}\n"
            f"Description: {result['description']}\n"
            f"Full response: {result.get('full_response', result.get('error'))}"
        )

    # ============================================================
    # CHITCHAT TESTS
    # ============================================================

    @pytest.mark.parametrize("test_case", CHITCHAT_TEST_CASES,
                             ids=[tc.description for tc in CHITCHAT_TEST_CASES])
    def test_chitchat_interpretation(self, test_case):
        """Test AI correctly interprets casual/chitchat messages."""
        result = self._test_case(test_case)

        assert result["passed"], (
            f"AI misinterpreted: '{result['message']}'\n"
            f"Expected: {result['expected']}, Got: {result['actual']}\n"
            f"Description: {result['description']}\n"
            f"Full response: {result.get('full_response', result.get('error'))}"
        )


class TestAIAccuracyReport:
    """
    Runs all AI accuracy tests and generates a summary report.
    Useful for getting an overall accuracy percentage.
    """

    @pytest.mark.slow
    def test_generate_accuracy_report(self, onboarded_user, capsys):
        """Generate a comprehensive accuracy report."""
        from services.ai_service import process_with_ai

        phone = onboarded_user["phone"]

        all_test_cases = (
            REMINDER_TEST_CASES +
            MEMORY_TEST_CASES +
            LIST_TEST_CASES +
            DELETE_TEST_CASES +
            CHITCHAT_TEST_CASES
        )

        results = []
        passed = 0
        failed = 0

        print("\n" + "="*60)
        print("AI ACCURACY TEST REPORT")
        print("="*60)

        for tc in all_test_cases:
            try:
                result = process_with_ai(tc.message, phone, context={})
                actual = result.get("action", "unknown")
                is_pass = actual == tc.expected_action

                if is_pass:
                    passed += 1
                    status = "[PASS]"
                else:
                    failed += 1
                    status = "[FAIL]"

                results.append({
                    "message": tc.message,
                    "expected": tc.expected_action,
                    "actual": actual,
                    "passed": is_pass,
                    "tags": tc.tags
                })

                if not is_pass:
                    print(f"\n{status}: {tc.description}")
                    print(f"  Input: '{tc.message}'")
                    print(f"  Expected: {tc.expected_action}")
                    print(f"  Got: {actual}")

            except Exception as e:
                failed += 1
                print(f"\n[ERROR]: {tc.description}")
                print(f"  Input: '{tc.message}'")
                print(f"  Error: {str(e)}")

        # Summary
        total = passed + failed
        accuracy = (passed / total * 100) if total > 0 else 0

        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Accuracy: {accuracy:.1f}%")
        print("="*60)

        # Group failures by tag
        failures_by_tag = {}
        for r in results:
            if not r["passed"]:
                for tag in r["tags"]:
                    if tag not in failures_by_tag:
                        failures_by_tag[tag] = []
                    failures_by_tag[tag].append(r["message"])

        if failures_by_tag:
            print("\nFailures by category:")
            for tag, messages in sorted(failures_by_tag.items()):
                print(f"  {tag}: {len(messages)} failures")

        # Assert a minimum accuracy threshold
        assert accuracy >= 70, f"AI accuracy below threshold: {accuracy:.1f}% (minimum 70%)"
