# Remyndrs Test Suite

Automated testing framework for the Remyndrs SMS reminder service.

## Quick Start

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
python run_tests.py

# Run quick tests only (skip slow integration tests)
python run_tests.py --quick

# Run with coverage report
python run_tests.py --coverage
```

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures and mocks
├── test_onboarding.py    # Onboarding flow tests
├── test_reminders.py     # Reminder creation/management tests
├── test_lists.py         # List management tests
├── test_memories.py      # Memory storage tests
├── test_edge_cases.py    # Edge cases and error handling
├── test_background_tasks.py  # Celery task tests
└── test_scenarios.py     # Full conversation scenarios
```

## Key Components

### ConversationSimulator

The `ConversationSimulator` class simulates user SMS interactions without sending real messages:

```python
# In your test
async def test_example(simulator, onboarded_user):
    result = await simulator.send_message(
        onboarded_user["phone"],
        "Remind me tomorrow at 2pm to call mom"
    )
    assert "remind" in result["output"].lower()
```

### SMSCapture

Captures all outbound SMS messages for verification:

```python
async def test_sms_sent(simulator, sms_capture, onboarded_user):
    await simulator.send_message(phone, "some message")

    # Check what was sent
    assert len(sms_capture.messages) > 0
    assert "expected text" in sms_capture.get_last_message()["message"]
```

### AIResponseMock

Mock AI responses for predictable testing:

```python
async def test_with_ai_mock(simulator, ai_mock, onboarded_user):
    # Set up expected AI response
    ai_mock.set_response("remind me tomorrow", {
        "action": "reminder",
        "reminder_text": "test",
        "reminder_date": "2025-01-01 14:00:00"
    })

    result = await simulator.send_message(phone, "remind me tomorrow")
```

## Available Fixtures

| Fixture | Description |
|---------|-------------|
| `simulator` | ConversationSimulator instance with mocked SMS/AI |
| `sms_capture` | SMSCapture instance to inspect sent messages |
| `ai_mock` | AIResponseMock to control AI responses |
| `test_phone` | Consistent test phone number |
| `onboarded_user` | Pre-created onboarded user (cleaned up after test) |
| `clean_test_user` | Phone number with guaranteed clean slate |
| `mock_datetime` | DateTime mocker for time-sensitive tests |

## Running Specific Tests

```bash
# By test file
python run_tests.py --onboarding
python run_tests.py --reminders
python run_tests.py --lists
python run_tests.py --memories
python run_tests.py --edge
python run_tests.py --tasks
python run_tests.py --scenarios

# By marker
pytest -m slow          # Only slow tests
pytest -m "not slow"    # Skip slow tests

# Single test
pytest tests/test_reminders.py::TestReminderCreation::test_reminder_with_specific_time

# Re-run failed tests
python run_tests.py --failed
```

## Writing New Tests

### Basic Test Structure

```python
import pytest

class TestFeatureName:
    """Tests for feature description."""

    @pytest.mark.asyncio
    async def test_basic_functionality(self, simulator, onboarded_user, ai_mock):
        """Test that basic functionality works."""
        phone = onboarded_user["phone"]

        # Set up AI mock if needed
        ai_mock.set_response("input message", {
            "action": "expected_action",
            # ... other fields
        })

        # Simulate user interaction
        result = await simulator.send_message(phone, "input message")

        # Verify response
        assert "expected" in result["output"].lower()

        # Verify database state if needed
        from models.reminder import get_user_reminders
        reminders = get_user_reminders(phone)
        assert len(reminders) == 1
```

### Testing Multi-Step Flows

```python
@pytest.mark.asyncio
@pytest.mark.slow  # Mark as slow for scenario tests
async def test_multi_step_flow(self, simulator, clean_test_user, ai_mock):
    """Test a complete multi-step user flow."""
    phone = clean_test_user

    # Step 1
    result = await simulator.send_message(phone, "first message")
    assert "expected step 1" in result["output"].lower()

    # Step 2
    result = await simulator.send_message(phone, "second message")
    assert "expected step 2" in result["output"].lower()

    # ... continue flow
```

### Testing Background Tasks

```python
@pytest.mark.asyncio
async def test_background_task(self, onboarded_user, sms_capture):
    """Test a Celery background task."""
    phone = onboarded_user["phone"]

    # Set up data
    from models.reminder import save_reminder
    save_reminder(phone, "test", "2025-01-01 00:00:00")

    # Run task with mocked SMS
    with patch('services.sms_service.send_sms', side_effect=sms_capture.send_sms):
        from tasks.reminder_tasks import check_and_send_reminders
        check_and_send_reminders()

    # Verify
    assert len(sms_capture.messages) > 0
```

## Test Database

Tests run against your configured PostgreSQL database. Each test that uses the `onboarded_user` or `clean_test_user` fixtures will:

1. Clean up any existing data for the test phone number
2. Create test data as needed
3. Run the test
4. Clean up all test data after completion

**Important**: Tests use a specific test phone number (`+15559876543` by default) to avoid conflicts with real user data.

## Coverage Reports

Run with coverage to see which code paths are tested:

```bash
python run_tests.py --coverage
```

This generates:
- Terminal output with coverage summary
- HTML report in `htmlcov/index.html`

## Troubleshooting

### Tests hang or timeout

- Check database connection is available
- Ensure Redis is running (for Celery tests)
- Check for infinite loops in pending state handling

### Import errors

- Run from project root directory
- Ensure all dependencies installed: `pip install -r requirements.txt`

### Database conflicts

- Tests should clean up after themselves
- If issues persist, manually clear test phone data:
  ```sql
  DELETE FROM users WHERE phone_number = '+15559876543';
  ```

### Mock not working

- Ensure patch path matches actual import
- Check that fixture is included in test parameters
