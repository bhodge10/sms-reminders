"""
End-to-End Flow Tests - Full conversation simulation with action execution.

These tests:
1. Process messages through the real AI
2. Execute actions and persist state to the database
3. Simulate complete multi-turn conversations
4. Generate a detailed markdown report for code improvements

Run with: test tests/test_e2e_flows.py -v -s
Generate report: test e2e (uses test.bat)
"""

import pytest
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
import pytz
import os

pytestmark = [pytest.mark.slow, pytest.mark.e2e]


class ActionExecutor:
    """
    Executes AI actions against the database, simulating real message flow.
    This mirrors what main.py does after getting AI response.
    """

    def __init__(self, phone_number):
        self.phone = phone_number
        self.conversation_log = []

    def process_and_execute(self, message):
        """
        Process a message through AI and execute the resulting action.
        Returns (action, response_message, success, details)
        """
        from services.ai_service import process_with_ai
        from models.user import create_or_update_user, get_user
        from models.reminder import save_reminder, save_reminder_with_local_time
        from models.memory import save_memory, get_memories, delete_memory
        from models.list_model import (
            create_list, get_lists, get_list_by_name, add_list_item,
            get_list_items, mark_item_complete, delete_list_item
        )
        from utils.timezone import get_user_current_time

        # Get AI interpretation
        result = process_and_execute(message, self.phone, context={})
        action = result.get("action", "unknown")

        response = ""
        success = True
        details = result

        try:
            # Execute based on action type
            if action == "reminder":
                reminder_text = result.get("reminder_text", "")
                reminder_date = result.get("reminder_date", "")
                if reminder_text and reminder_date:
                    save_reminder(self.phone, reminder_text, reminder_date)
                    response = result.get("confirmation", f"Reminder set: {reminder_text}")
                else:
                    success = False
                    response = "Missing reminder details"

            elif action == "reminder_relative":
                reminder_text = result.get("reminder_text", "")
                offset_minutes = result.get("offset_minutes", 0)
                offset_days = result.get("offset_days", 0)
                if reminder_text:
                    user_time = get_user_current_time(self.phone)
                    if offset_minutes:
                        reminder_dt = user_time + timedelta(minutes=offset_minutes)
                    elif offset_days:
                        reminder_dt = user_time + timedelta(days=offset_days)
                    else:
                        reminder_dt = user_time + timedelta(hours=1)
                    save_reminder(self.phone, reminder_text, reminder_dt.strftime('%Y-%m-%d %H:%M:%S'))
                    response = f"Reminder set for {reminder_dt.strftime('%I:%M %p')}: {reminder_text}"
                else:
                    success = False
                    response = "Missing reminder text"

            elif action == "clarify_time":
                # Set pending state for time clarification
                reminder_text = result.get("reminder_text", "")
                time_mentioned = result.get("time_mentioned", "")
                create_or_update_user(self.phone,
                                      pending_reminder_text=reminder_text,
                                      pending_reminder_time=time_mentioned)
                response = result.get("response", f"Do you mean {time_mentioned} AM or PM?")

            elif action == "clarify_date_time":
                # Set pending state for date/time clarification
                reminder_text = result.get("reminder_text", "")
                reminder_date = result.get("reminder_date", "")
                create_or_update_user(self.phone,
                                      pending_reminder_text=reminder_text,
                                      pending_reminder_date=reminder_date)
                response = result.get("response", "What time would you like the reminder?")

            elif action == "store":
                memory_text = result.get("memory_text", "")
                if memory_text:
                    # save_memory requires: phone_number, memory_text, parsed_data
                    parsed_data = json.dumps({"raw": memory_text})
                    save_memory(self.phone, memory_text, parsed_data)
                    response = result.get("confirmation", f"Stored: {memory_text}")
                else:
                    success = False
                    response = "Missing memory text"

            elif action == "retrieve":
                response = result.get("response", "")
                if not response:
                    success = False

            elif action == "create_list":
                list_name = result.get("list_name", "")
                if list_name:
                    create_list(self.phone, list_name)
                    response = result.get("confirmation", f"Created {list_name}")
                else:
                    success = False
                    response = "Missing list name"

            elif action == "add_to_list":
                list_name = result.get("list_name", "")
                item_text = result.get("item_text", "")
                if list_name and item_text:
                    # Auto-create list if it doesn't exist
                    if not get_list_by_name(self.phone, list_name):
                        create_list(self.phone, list_name)
                    list_info = get_list_by_name(self.phone, list_name)
                    if list_info:
                        # add_list_item requires: list_id, phone_number, item_text
                        add_list_item(list_info[0], self.phone, item_text)
                        response = result.get("confirmation", f"Added {item_text} to {list_name}")
                    else:
                        success = False
                        response = f"Could not find or create list: {list_name}"
                else:
                    success = False
                    response = "Missing list name or item"

            elif action == "show_list":
                list_name = result.get("list_name", "")
                list_info = get_list_by_name(self.phone, list_name)
                if list_info:
                    items = get_list_items(list_info[0])
                    if items:
                        item_texts = [f"{i+1}. {item[1]}" for i, item in enumerate(items)]
                        response = f"{list_name}:\n" + "\n".join(item_texts)
                    else:
                        response = f"Your {list_name} is empty."
                else:
                    response = f"List '{list_name}' not found."
                    success = False

            elif action == "show_all_lists":
                lists = get_lists(self.phone)
                if lists:
                    list_names = [f"{i+1}. {lst[1]}" for i, lst in enumerate(lists)]
                    response = "Your lists:\n" + "\n".join(list_names)
                else:
                    response = "You don't have any lists yet."

            elif action == "delete_memory":
                search_term = result.get("search_term", "")
                memories = get_memories(self.phone)
                found = None
                for m in memories:
                    if search_term.lower() in m[1].lower():
                        found = m
                        break
                if found:
                    delete_memory(self.phone, found[0])
                    response = f"Deleted memory about {search_term}"
                else:
                    response = f"No memory found about '{search_term}'"
                    success = False

            elif action == "help":
                response = result.get("response", "How can I help you?")

            elif action == "show_help":
                response = result.get("response", "Text INFO for the full guide.")

            else:
                response = result.get("response") or result.get("confirmation") or f"Action: {action}"

        except Exception as e:
            success = False
            response = f"Error executing {action}: {str(e)}"

        # Log this turn
        self.conversation_log.append({
            "message": message,
            "action": action,
            "response": response,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })

        return action, response, success, details

    def handle_clarification_response(self, response_msg):
        """
        Handle follow-up messages like 'PM', 'AM', 'Yes', numbers, etc.
        These need the pending state from a previous message.
        """
        from models.user import get_user, create_or_update_user, get_pending_reminder_date
        from models.reminder import save_reminder
        from utils.timezone import get_user_current_time
        import pytz

        user = get_user(self.phone)
        response_upper = response_msg.upper().strip()

        # Check for pending time clarification (AM/PM response)
        if user and len(user) > 11 and user[10] and user[11]:  # pending_reminder_text and pending_reminder_time
            pending_text = user[10]
            pending_time = user[11]

            if response_upper in ['AM', 'PM', 'A.M.', 'P.M.', 'A', 'P']:
                am_pm = 'AM' if response_upper.startswith('A') else 'PM'

                try:
                    user_time = get_user_current_time(self.phone)

                    # Parse time
                    clean_time = pending_time.replace("AM", "").replace("PM", "").strip()
                    parts = clean_time.split(":")
                    hour = int(parts[0])
                    minute = int(parts[1]) if len(parts) > 1 else 0

                    # Convert to 24-hour
                    if am_pm == "PM" and hour != 12:
                        hour += 12
                    elif am_pm == "AM" and hour == 12:
                        hour = 0

                    reminder_dt = user_time.replace(hour=hour, minute=minute, second=0)
                    if reminder_dt <= user_time:
                        reminder_dt += timedelta(days=1)

                    # Convert to UTC and save
                    reminder_utc = reminder_dt.astimezone(pytz.UTC)
                    save_reminder(self.phone, pending_text, reminder_utc.strftime('%Y-%m-%d %H:%M:%S'))

                    # Clear pending
                    create_or_update_user(self.phone, pending_reminder_text=None, pending_reminder_time=None)

                    response = f"Reminder set for {reminder_dt.strftime('%A at %I:%M %p')}: {pending_text}"
                    self.conversation_log.append({
                        "message": response_msg,
                        "action": "reminder_confirmed",
                        "response": response,
                        "success": True,
                        "timestamp": datetime.now().isoformat()
                    })
                    return "reminder_confirmed", response, True, {}

                except Exception as e:
                    return "error", f"Error: {str(e)}", False, {}

        # Check for pending date/time clarification
        pending_date_data = get_pending_reminder_date(self.phone)
        if pending_date_data:
            # Look for time in response
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?', response_msg, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                am_pm = time_match.group(3)

                if am_pm:
                    am_pm = am_pm.lower().replace('.', '')
                    if am_pm in ['pm', 'p'] and hour != 12:
                        hour += 12
                    elif am_pm in ['am', 'a'] and hour == 12:
                        hour = 0

                    try:
                        from models.user import get_user_timezone
                        tz = pytz.timezone(get_user_timezone(self.phone))

                        reminder_date = datetime.strptime(pending_date_data['date'], '%Y-%m-%d')
                        reminder_dt = reminder_date.replace(hour=hour, minute=minute)
                        aware_dt = tz.localize(reminder_dt)
                        utc_dt = aware_dt.astimezone(pytz.UTC)

                        save_reminder(self.phone, pending_date_data['text'], utc_dt.strftime('%Y-%m-%d %H:%M:%S'))
                        create_or_update_user(self.phone, pending_reminder_text=None, pending_reminder_date=None)

                        response = f"Reminder set for {aware_dt.strftime('%A at %I:%M %p')}: {pending_date_data['text']}"
                        self.conversation_log.append({
                            "message": response_msg,
                            "action": "reminder_date_time_confirmed",
                            "response": response,
                            "success": True,
                            "timestamp": datetime.now().isoformat()
                        })
                        return "reminder_date_time_confirmed", response, True, {}

                    except Exception as e:
                        return "error", f"Error: {str(e)}", False, {}

        # Fall back to AI processing
        return self.process_and_execute(response_msg)


def process_and_execute(message, phone, context):
    """Wrapper to call AI service."""
    from services.ai_service import process_with_ai
    return process_with_ai(message, phone, context)


class E2ETestScenario:
    """Represents a complete end-to-end test scenario."""

    def __init__(self, name, description, messages, expected_outcomes, category, tags=None):
        self.name = name
        self.description = description
        self.messages = messages  # List of messages to send
        self.expected_outcomes = expected_outcomes  # List of expected (action, keywords) tuples
        self.category = category
        self.tags = tags or []
        self.results = []
        self.passed = False
        self.failure_reason = ""


# ============================================================
# TEST SCENARIOS - Complete user journeys
# ============================================================

REMINDER_SCENARIOS = [
    E2ETestScenario(
        name="Complete reminder in one message",
        description="User provides all info upfront",
        messages=["remind me tomorrow at 3pm to take medicine"],
        expected_outcomes=[("reminder", ["medicine", "3"])],
        category="reminder",
        tags=["basic", "one_shot"]
    ),
    E2ETestScenario(
        name="Reminder with time clarification",
        description="User needs to clarify AM/PM",
        messages=["remind me at 4 to call mom", "PM"],
        expected_outcomes=[
            ("clarify_time", ["4", "AM", "PM"]),
            ("reminder_confirmed", ["call mom"])
        ],
        category="reminder",
        tags=["multi_turn", "clarification"]
    ),
    E2ETestScenario(
        name="Reminder with date clarification",
        description="User provides date but no time",
        messages=["remind me tomorrow to check email", "9am"],
        expected_outcomes=[
            ("clarify_date_time", ["time", "tomorrow"]),
            ("reminder_date_time_confirmed", ["email"])
        ],
        category="reminder",
        tags=["multi_turn", "clarification"]
    ),
    E2ETestScenario(
        name="Relative time reminder",
        description="In X minutes reminder",
        messages=["remind me in 30 minutes to check the oven"],
        expected_outcomes=[("reminder_relative", ["oven"])],
        category="reminder",
        tags=["basic", "relative"]
    ),
    E2ETestScenario(
        name="Reminder with typos",
        description="Common typos should still work",
        messages=["remid me tomorow at 3pm to call doctor"],
        expected_outcomes=[("reminder", ["doctor", "3"])],
        category="reminder",
        tags=["typo", "robustness"]
    ),
]

MEMORY_SCENARIOS = [
    E2ETestScenario(
        name="Store and retrieve memory",
        description="Basic memory storage and retrieval",
        messages=[
            "remember my wifi password is TestPass123",
            "what is my wifi password"
        ],
        expected_outcomes=[
            ("store", ["wifi", "TestPass123"]),
            ("retrieve", ["TestPass123"])
        ],
        category="memory",
        tags=["basic", "multi_turn"]
    ),
    E2ETestScenario(
        name="Store with 'that' phrasing",
        description="Remember that... phrasing",
        messages=["remember that john's birthday is march 15"],
        expected_outcomes=[("store", ["john", "birthday", "march"])],
        category="memory",
        tags=["basic", "phrasing"]
    ),
]

LIST_SCENARIOS = [
    E2ETestScenario(
        name="Create list and add items",
        description="Full list workflow",
        messages=[
            "create a grocery list",
            "add milk to grocery list",
            "add eggs to grocery list",
            "show grocery list"
        ],
        expected_outcomes=[
            ("create_list", ["grocery"]),
            ("add_to_list", ["milk"]),
            ("add_to_list", ["eggs"]),
            ("show_list", ["milk", "eggs"])
        ],
        category="list",
        tags=["basic", "multi_turn"]
    ),
    E2ETestScenario(
        name="Add multiple items at once",
        description="Add comma-separated items",
        messages=[
            "create a shopping list",
            "add bread, butter, cheese to shopping list"
        ],
        expected_outcomes=[
            ("create_list", ["shopping"]),
            ("add_to_list", ["bread"])  # Should contain all items ideally
        ],
        category="list",
        tags=["multi_item"]
    ),
]

EDGE_CASE_SCENARIOS = [
    E2ETestScenario(
        name="Greeting response",
        description="Hello should get friendly help",
        messages=["hello"],
        expected_outcomes=[("help", ["help", "Hi"])],
        category="chitchat",
        tags=["basic"]
    ),
    E2ETestScenario(
        name="Help request",
        description="User asks for help",
        messages=["what can you do"],
        expected_outcomes=[("show_help", ["remind", "remember", "list"])],
        category="chitchat",
        tags=["basic"]
    ),
    E2ETestScenario(
        name="Ambiguous delete",
        description="Delete without context",
        messages=["delete 1"],
        expected_outcomes=[("help", [])],  # Should ask for clarification
        category="edge_case",
        tags=["ambiguous", "context_needed"]
    ),
]

ALL_SCENARIOS = REMINDER_SCENARIOS + MEMORY_SCENARIOS + LIST_SCENARIOS + EDGE_CASE_SCENARIOS


class TestE2EFlows:
    """End-to-end flow tests with action execution."""

    @pytest.fixture(autouse=True)
    def setup(self, onboarded_user, sms_capture):
        """Setup test user."""
        self.phone = onboarded_user["phone"]
        self.sms_capture = sms_capture

    def run_scenario(self, scenario):
        """Run a single test scenario."""
        executor = ActionExecutor(self.phone)
        scenario.results = []

        for i, message in enumerate(scenario.messages):
            expected_action, expected_keywords = scenario.expected_outcomes[i] if i < len(scenario.expected_outcomes) else (None, [])

            # Check if this is a clarification response
            if message.upper().strip() in ['AM', 'PM', 'YES', 'NO'] or re.match(r'^\d{1,2}(:\d{2})?\s*(am|pm)?$', message, re.IGNORECASE):
                action, response, success, details = executor.handle_clarification_response(message)
            else:
                action, response, success, details = executor.process_and_execute(message)

            # Check if outcome matches expectations
            action_match = expected_action is None or action == expected_action
            keywords_match = all(kw.lower() in response.lower() for kw in expected_keywords) if expected_keywords else True

            scenario.results.append({
                "message": message,
                "expected_action": expected_action,
                "actual_action": action,
                "expected_keywords": expected_keywords,
                "response": response,
                "action_match": action_match,
                "keywords_match": keywords_match,
                "success": success
            })

        # Scenario passes if all turns match
        scenario.passed = all(r["action_match"] and r["keywords_match"] for r in scenario.results)
        if not scenario.passed:
            failures = [r for r in scenario.results if not r["action_match"] or not r["keywords_match"]]
            if failures:
                f = failures[0]
                scenario.failure_reason = f"Expected {f['expected_action']}, got {f['actual_action']}. Response: {f['response'][:100]}"

        return scenario

    @pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=[s.name for s in ALL_SCENARIOS])
    def test_scenario(self, scenario):
        """Test each scenario."""
        result = self.run_scenario(scenario)
        assert result.passed, f"{scenario.name}: {scenario.failure_reason}"


class TestE2EReport:
    """Generate comprehensive E2E test report."""

    @pytest.fixture(autouse=True)
    def setup(self, onboarded_user, sms_capture):
        """Setup for report."""
        self.phone = onboarded_user["phone"]
        self.sms_capture = sms_capture

    @pytest.mark.slow
    def test_generate_e2e_report(self):
        """Run all scenarios and generate detailed report."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "total": 0,
            "passed": 0,
            "failed": 0,
            "by_category": defaultdict(lambda: {"passed": 0, "failed": 0, "scenarios": []}),
            "failures": [],
            "all_scenarios": []
        }

        for scenario in ALL_SCENARIOS:
            executor = ActionExecutor(self.phone)
            scenario.results = []

            for i, message in enumerate(scenario.messages):
                expected_action, expected_keywords = scenario.expected_outcomes[i] if i < len(scenario.expected_outcomes) else (None, [])

                if message.upper().strip() in ['AM', 'PM', 'YES', 'NO'] or re.match(r'^\d{1,2}(:\d{2})?\s*(am|pm)?$', message, re.IGNORECASE):
                    action, response, success, details = executor.handle_clarification_response(message)
                else:
                    action, response, success, details = executor.process_and_execute(message)

                action_match = expected_action is None or action == expected_action
                keywords_match = all(kw.lower() in response.lower() for kw in expected_keywords) if expected_keywords else True

                scenario.results.append({
                    "message": message,
                    "expected_action": expected_action,
                    "actual_action": action,
                    "expected_keywords": expected_keywords,
                    "response": response[:200],
                    "action_match": action_match,
                    "keywords_match": keywords_match
                })

            scenario.passed = all(r["action_match"] and r["keywords_match"] for r in scenario.results)
            results["total"] += 1

            if scenario.passed:
                results["passed"] += 1
                results["by_category"][scenario.category]["passed"] += 1
            else:
                results["failed"] += 1
                results["by_category"][scenario.category]["failed"] += 1
                failures = [r for r in scenario.results if not r["action_match"] or not r["keywords_match"]]
                if failures:
                    f = failures[0]
                    scenario.failure_reason = f"Expected {f['expected_action']}, got {f['actual_action']}"
                results["failures"].append({
                    "name": scenario.name,
                    "category": scenario.category,
                    "description": scenario.description,
                    "messages": scenario.messages,
                    "results": scenario.results,
                    "tags": scenario.tags
                })

            results["by_category"][scenario.category]["scenarios"].append({
                "name": scenario.name,
                "passed": scenario.passed,
                "tags": scenario.tags
            })
            results["all_scenarios"].append(scenario)

        # Generate markdown report
        self._generate_markdown_report(results)

        # Print summary
        accuracy = (results["passed"] / results["total"] * 100) if results["total"] > 0 else 0
        print(f"\n{'='*60}")
        print("E2E TEST REPORT SUMMARY")
        print(f"{'='*60}")
        print(f"Total scenarios: {results['total']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Accuracy: {accuracy:.1f}%")
        print(f"\nBy Category:")
        for cat, data in results["by_category"].items():
            cat_total = data["passed"] + data["failed"]
            cat_pct = (data["passed"] / cat_total * 100) if cat_total > 0 else 0
            print(f"  {cat}: {data['passed']}/{cat_total} ({cat_pct:.0f}%)")
        print(f"\nMarkdown report saved to: tests/E2E_TEST_REPORT.md")

        assert accuracy >= 50, f"E2E accuracy below threshold: {accuracy:.1f}%"

    def _generate_markdown_report(self, results):
        """Generate detailed markdown report."""
        accuracy = (results["passed"] / results["total"] * 100) if results["total"] > 0 else 0

        md = f"""# End-to-End Test Report

Generated: {results['timestamp']}

## Summary

| Metric | Value |
|--------|-------|
| Total Scenarios | {results['total']} |
| Passed | {results['passed']} |
| Failed | {results['failed']} |
| **Accuracy** | **{accuracy:.1f}%** |

## Results by Category

| Category | Passed | Failed | Success Rate |
|----------|--------|--------|--------------|
"""
        for cat, data in results["by_category"].items():
            cat_total = data["passed"] + data["failed"]
            cat_pct = (data["passed"] / cat_total * 100) if cat_total > 0 else 0
            md += f"| {cat} | {data['passed']} | {data['failed']} | {cat_pct:.0f}% |\n"

        if results["failures"]:
            md += f"""

## Failed Scenarios

The following scenarios failed and need attention:

"""
            for failure in results["failures"]:
                md += f"""### {failure['name']}

**Category:** {failure['category']}
**Description:** {failure['description']}
**Tags:** {', '.join(failure['tags'])}

**Conversation:**
"""
                for r in failure["results"]:
                    status = "[PASS]" if r["action_match"] and r["keywords_match"] else "[FAIL]"
                    md += f"""
- **User:** "{r['message']}"
- **Expected:** {r['expected_action']} (keywords: {r['expected_keywords']})
- **Got:** {r['actual_action']} {status}
- **Response:** {r['response'][:150]}...
"""
                md += "\n---\n"

            md += """

## Recommended Code Improvements

Based on the failed scenarios, here are recommended improvements:

"""
            # Analyze failures and generate recommendations
            failure_patterns = defaultdict(list)
            for f in results["failures"]:
                for tag in f["tags"]:
                    failure_patterns[tag].append(f["name"])

            if "multi_turn" in failure_patterns:
                md += """### 1. Multi-Turn Conversation Handling

**Issue:** Context is lost between conversation turns.

**Files to modify:**
- `main.py` - Add better state tracking
- `models/user.py` - Ensure pending states are properly set/cleared

**Recommended changes:**
```python
# In main.py, ensure clarify_time action sets state:
if action == "clarify_time":
    create_or_update_user(phone_number,
        pending_reminder_text=result.get("reminder_text"),
        pending_reminder_time=result.get("time_mentioned"))
```

"""

            if "clarification" in failure_patterns:
                md += """### 2. Time/Date Clarification Flow

**Issue:** Follow-up responses (AM/PM, time) not being processed correctly.

**Files to modify:**
- `main.py` - Lines 445-575 (clarification handlers)
- `services/ai_service.py` - Ensure clarify_time returns proper fields

**Recommended changes:**
```python
# Ensure AI returns required fields for clarification:
# clarify_time must include: reminder_text, time_mentioned
# clarify_date_time must include: reminder_text, reminder_date
```

"""

            if "multi_item" in failure_patterns:
                md += """### 3. Multi-Item List Additions

**Issue:** When adding multiple items (e.g., "add milk, eggs, bread"), only first item is added.

**Files to modify:**
- `services/ai_service.py` - parse_list_items function
- `main.py` - add_to_list handler

**Recommended changes:**
```python
# In main.py add_to_list handler:
from services.ai_service import parse_list_items

item_text = result.get("item_text", "")
items = parse_list_items(item_text)  # Returns list of individual items
for item in items:
    add_list_item(list_id, item)
```

"""

            if "context_needed" in failure_patterns:
                md += """### 4. Context-Dependent Commands

**Issue:** Commands like "delete 1", "yes", "new" need conversation context to work.

**Files to modify:**
- `main.py` - Add context tracking for ambiguous commands
- `models/user.py` - Add `last_command_context` field

**Recommended changes:**
```python
# Track what context "1" or "yes" refers to:
# After showing numbered list, set:
create_or_update_user(phone_number,
    last_command_context="delete_options",
    pending_delete_options=json.dumps(options))
```

"""

        md += f"""

## Test Commands

Run these tests:
```bash
# Run all E2E tests
test e2e

# Run specific category
test tests/test_e2e_flows.py -v -k "reminder"

# Generate this report
test tests/test_e2e_flows.py::TestE2EReport -v -s
```

## Comparison: Single-Message vs E2E Accuracy

| Test Type | Accuracy | What It Measures |
|-----------|----------|------------------|
| Single-Message AI | ~95% | AI intent classification on isolated messages |
| **E2E Conversation Flows** | **{accuracy:.0f}%** | Real multi-turn conversations with state |

The gap between these numbers represents bugs in:
1. State management between messages
2. Action execution after AI interpretation
3. Context handling for follow-up messages

---

*Generated by test_e2e_flows.py*
"""

        # Save report
        report_path = os.path.join(os.path.dirname(__file__), "E2E_TEST_REPORT.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md)
