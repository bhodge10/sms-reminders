# End-to-End Test Report

Generated: 2026-01-19T07:49:33.218224

## Summary

| Metric | Value |
|--------|-------|
| Total Scenarios | 12 |
| Passed | 0 |
| Failed | 12 |
| **Accuracy** | **0.0%** |

## Results by Category

| Category | Passed | Failed | Success Rate |
|----------|--------|--------|--------------|
| reminder | 0 | 5 | 0% |
| memory | 0 | 2 | 0% |
| list | 0 | 2 | 0% |
| chitchat | 0 | 2 | 0% |
| edge_case | 0 | 1 | 0% |


## Failed Scenarios

The following scenarios failed and need attention:

### Complete reminder in one message

**Category:** reminder
**Description:** User provides all info upfront
**Tags:** basic, one_shot

**Conversation:**

- **User:** "remind me tomorrow at 3pm to take medicine"
- **Expected:** reminder (keywords: ['medicine', '3'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

---
### Reminder with time clarification

**Category:** reminder
**Description:** User needs to clarify AM/PM
**Tags:** multi_turn, clarification

**Conversation:**

- **User:** "remind me at 4 to call mom"
- **Expected:** clarify_time (keywords: ['4', 'AM', 'PM'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

- **User:** "PM"
- **Expected:** reminder_confirmed (keywords: ['call mom'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

---
### Reminder with date clarification

**Category:** reminder
**Description:** User provides date but no time
**Tags:** multi_turn, clarification

**Conversation:**

- **User:** "remind me tomorrow to check email"
- **Expected:** clarify_date_time (keywords: ['time', 'tomorrow'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

- **User:** "9am"
- **Expected:** reminder_date_time_confirmed (keywords: ['email'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

---
### Relative time reminder

**Category:** reminder
**Description:** In X minutes reminder
**Tags:** basic, relative

**Conversation:**

- **User:** "remind me in 30 minutes to check the oven"
- **Expected:** reminder_relative (keywords: ['oven'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

---
### Reminder with typos

**Category:** reminder
**Description:** Common typos should still work
**Tags:** typo, robustness

**Conversation:**

- **User:** "remid me tomorow at 3pm to call doctor"
- **Expected:** reminder (keywords: ['doctor', '3'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

---
### Store and retrieve memory

**Category:** memory
**Description:** Basic memory storage and retrieval
**Tags:** basic, multi_turn

**Conversation:**

- **User:** "remember my wifi password is TestPass123"
- **Expected:** store (keywords: ['wifi', 'TestPass123'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

- **User:** "what is my wifi password"
- **Expected:** retrieve (keywords: ['TestPass123'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

---
### Store with 'that' phrasing

**Category:** memory
**Description:** Remember that... phrasing
**Tags:** basic, phrasing

**Conversation:**

- **User:** "remember that john's birthday is march 15"
- **Expected:** store (keywords: ['john', 'birthday', 'march'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

---
### Create list and add items

**Category:** list
**Description:** Full list workflow
**Tags:** basic, multi_turn

**Conversation:**

- **User:** "create a grocery list"
- **Expected:** create_list (keywords: ['grocery'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

- **User:** "add milk to grocery list"
- **Expected:** add_to_list (keywords: ['milk'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

- **User:** "add eggs to grocery list"
- **Expected:** add_to_list (keywords: ['eggs'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

- **User:** "show grocery list"
- **Expected:** show_list (keywords: ['milk', 'eggs'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

---
### Add multiple items at once

**Category:** list
**Description:** Add comma-separated items
**Tags:** multi_item

**Conversation:**

- **User:** "create a shopping list"
- **Expected:** create_list (keywords: ['shopping'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

- **User:** "add bread, butter, cheese to shopping list"
- **Expected:** add_to_list (keywords: ['bread'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

---
### Greeting response

**Category:** chitchat
**Description:** Hello should get friendly help
**Tags:** basic

**Conversation:**

- **User:** "hello"
- **Expected:** help (keywords: ['help', 'Hi'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

---
### Help request

**Category:** chitchat
**Description:** User asks for help
**Tags:** basic

**Conversation:**

- **User:** "what can you do"
- **Expected:** show_help (keywords: ['remind', 'remember', 'list'])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

---
### Ambiguous delete

**Category:** edge_case
**Description:** Delete without context
**Tags:** ambiguous, context_needed

**Conversation:**

- **User:** "delete 1"
- **Expected:** help (keywords: [])
- **Got:** unknown [FAIL]
- **Response:** Mock AI response...

---


## Recommended Code Improvements

Based on the failed scenarios, here are recommended improvements:

### 1. Multi-Turn Conversation Handling

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

### 2. Time/Date Clarification Flow

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

### 3. Multi-Item List Additions

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

### 4. Context-Dependent Commands

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
| **E2E Conversation Flows** | **0%** | Real multi-turn conversations with state |

The gap between these numbers represents bugs in:
1. State management between messages
2. Action execution after AI interpretation
3. Context handling for follow-up messages

---

*Generated by test_e2e_flows.py*
