"""
Tests for Smart Nudges: proactive AI intelligence layer.
Covers nudge service functions, tier gating, keyword handlers,
response handling, and Celery task behavior.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, date, timedelta


# =====================================================
# NUDGE SERVICE UNIT TESTS
# =====================================================

class TestNudgeEligibility:
    """Test tier-based nudge eligibility."""

    def test_premium_eligible_any_day(self):
        from services.nudge_service import is_nudge_eligible
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            assert is_nudge_eligible('premium', day) is True

    def test_free_eligible_only_sunday(self):
        from services.nudge_service import is_nudge_eligible
        assert is_nudge_eligible('free', 'Sunday') is True
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']:
            assert is_nudge_eligible('free', day) is False

    def test_trial_eligible_any_day(self):
        """Trial users have premium status, eligible daily."""
        from services.nudge_service import is_nudge_eligible
        assert is_nudge_eligible('premium', 'Monday') is True


class TestBuildNudgePrompt:
    """Test AI prompt construction."""

    def test_prompt_contains_user_data(self):
        from services.nudge_service import build_nudge_prompt
        user_data = {
            'current_date': '2026-02-23',
            'current_day': 'Monday',
            'memories': [{'text': 'Mom birthday March 15', 'created_at': '2026-01-01'}],
            'upcoming_reminders': [{'id': 1, 'text': 'Call dentist', 'date': '2026-02-24 02:00 PM', 'is_recurring': False}],
            'recently_completed_reminders': [],
            'lists': [{'name': 'Groceries', 'total_items': 3, 'completed_items': 1, 'items': [{'text': 'Milk', 'completed': False}]}],
            'recent_nudges': [],
        }
        prompt = build_nudge_prompt(user_data, 'Brad', 'premium')
        assert 'Brad' in prompt
        assert 'Mom birthday March 15' in prompt
        assert 'Call dentist' in prompt
        assert 'Groceries' in prompt

    def test_free_tier_restricts_to_weekly_reflection(self):
        from services.nudge_service import build_nudge_prompt
        user_data = {
            'current_date': '2026-02-23',
            'current_day': 'Sunday',
            'memories': [], 'upcoming_reminders': [],
            'recently_completed_reminders': [], 'lists': [],
            'recent_nudges': [],
        }
        prompt = build_nudge_prompt(user_data, 'User', 'free')
        assert 'weekly_reflection' in prompt
        assert 'MUST generate a weekly_reflection' in prompt

    def test_recent_nudges_included_in_prompt(self):
        from services.nudge_service import build_nudge_prompt
        user_data = {
            'current_date': '2026-02-23',
            'current_day': 'Monday',
            'memories': [], 'upcoming_reminders': [],
            'recently_completed_reminders': [], 'lists': [],
            'recent_nudges': [{'type': 'date_extraction', 'text': 'Previous nudge', 'sent_at': '2026-02-22'}],
        }
        prompt = build_nudge_prompt(user_data, 'User', 'premium')
        assert 'Previous nudge' in prompt
        assert 'DO NOT repeat' in prompt


class TestGenerateNudge:
    """Test nudge generation with mocked OpenAI."""

    @patch('services.nudge_service.log_api_usage')
    @patch('services.nudge_service.OpenAI')
    @patch('services.nudge_service.gather_user_data')
    def test_generates_nudge_successfully(self, mock_gather, mock_openai_cls, mock_log):
        from services.nudge_service import generate_nudge

        mock_gather.return_value = {
            'current_date': '2026-02-23', 'current_day': 'Monday',
            'memories': [{'text': 'Test', 'created_at': '2026-01-01'}],
            'upcoming_reminders': [], 'recently_completed_reminders': [],
            'lists': [], 'recent_nudges': [],
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            'nudge_type': 'date_extraction',
            'nudge_text': 'Hey Brad! You saved "Mom birthday March 15". Want me to set a reminder for March 14?',
            'confidence': 85,
            'suggested_reminder_text': 'Mom birthday tomorrow',
        })
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        mock_openai_cls.return_value.chat.completions.create.return_value = mock_response

        result = generate_nudge('+15551234567', 'America/New_York', 'Brad', 'premium')

        assert result is not None
        assert result['nudge_type'] == 'date_extraction'
        assert 'Mom birthday' in result['nudge_text']
        assert result['confidence'] == 85

    @patch('services.nudge_service.log_api_usage')
    @patch('services.nudge_service.OpenAI')
    @patch('services.nudge_service.gather_user_data')
    def test_skips_low_confidence_nudge(self, mock_gather, mock_openai_cls, mock_log):
        from services.nudge_service import generate_nudge

        mock_gather.return_value = {
            'current_date': '2026-02-23', 'current_day': 'Monday',
            'memories': [{'text': 'Test', 'created_at': '2026-01-01'}],
            'upcoming_reminders': [], 'recently_completed_reminders': [],
            'lists': [], 'recent_nudges': [],
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            'nudge_type': 'reminder_followup',
            'nudge_text': 'Some nudge',
            'confidence': 30,
        })
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        mock_openai_cls.return_value.chat.completions.create.return_value = mock_response

        result = generate_nudge('+15551234567', 'America/New_York', 'Brad', 'premium')
        assert result is None

    @patch('services.nudge_service.log_api_usage')
    @patch('services.nudge_service.OpenAI')
    @patch('services.nudge_service.gather_user_data')
    def test_skips_none_nudge_type(self, mock_gather, mock_openai_cls, mock_log):
        from services.nudge_service import generate_nudge

        mock_gather.return_value = {
            'current_date': '2026-02-23', 'current_day': 'Monday',
            'memories': [{'text': 'Test', 'created_at': '2026-01-01'}],
            'upcoming_reminders': [], 'recently_completed_reminders': [],
            'lists': [], 'recent_nudges': [],
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            'nudge_type': 'none',
            'nudge_text': '',
            'confidence': 90,
        })
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        mock_openai_cls.return_value.chat.completions.create.return_value = mock_response

        result = generate_nudge('+15551234567', 'America/New_York', 'Brad', 'premium')
        assert result is None

    @patch('services.nudge_service.gather_user_data')
    def test_skips_user_with_no_data(self, mock_gather):
        from services.nudge_service import generate_nudge

        mock_gather.return_value = {
            'current_date': '2026-02-23', 'current_day': 'Monday',
            'memories': [], 'upcoming_reminders': [],
            'recently_completed_reminders': [], 'lists': [],
            'recent_nudges': [],
        }

        result = generate_nudge('+15551234567', 'America/New_York', 'Brad', 'premium')
        assert result is None

    @patch('services.nudge_service.log_api_usage')
    @patch('services.nudge_service.OpenAI')
    @patch('services.nudge_service.gather_user_data')
    def test_truncates_long_nudge_text(self, mock_gather, mock_openai_cls, mock_log):
        from services.nudge_service import generate_nudge

        mock_gather.return_value = {
            'current_date': '2026-02-23', 'current_day': 'Monday',
            'memories': [{'text': 'Test', 'created_at': '2026-01-01'}],
            'upcoming_reminders': [], 'recently_completed_reminders': [],
            'lists': [], 'recent_nudges': [],
        }

        long_text = 'A' * 300  # Over 280 char limit
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            'nudge_type': 'weekly_reflection',
            'nudge_text': long_text,
            'confidence': 80,
        })
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        mock_openai_cls.return_value.chat.completions.create.return_value = mock_response

        result = generate_nudge('+15551234567', 'America/New_York', 'Brad', 'premium')
        assert result is not None
        assert len(result['nudge_text']) <= 280


class TestNudgeResponseHandling:
    """Test handling of user responses to nudges."""

    def _make_pending(self, nudge_type='date_extraction', suggested_reminder='Test reminder'):
        return {
            'nudge_id': 1,
            'nudge_type': nudge_type,
            'suggested_reminder_text': suggested_reminder,
            'related_reminder_id': None,
        }

    @patch('services.nudge_service.record_nudge_response')
    @patch('services.nudge_service.create_or_update_user')
    def test_stop_disables_nudges(self, mock_update, mock_record):
        from services.nudge_service import handle_nudge_response
        result = handle_nudge_response('+15551234567', 'STOP', self._make_pending())
        assert 'disabled' in result.lower()
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs['smart_nudges_enabled'] is False

    @patch('services.nudge_service.record_nudge_response')
    @patch('services.nudge_service.create_or_update_user')
    def test_no_dismisses_nudge(self, mock_update, mock_record):
        from services.nudge_service import handle_nudge_response
        result = handle_nudge_response('+15551234567', 'NO', self._make_pending())
        assert result == "Got it!"

    @patch('services.nudge_service._create_reminder_from_nudge', return_value=42)
    @patch('services.nudge_service.record_nudge_response')
    @patch('services.nudge_service.create_or_update_user')
    def test_yes_creates_reminder_for_date_extraction(self, mock_update, mock_record, mock_create):
        from services.nudge_service import handle_nudge_response
        result = handle_nudge_response('+15551234567', 'YES', self._make_pending())
        assert 'Reminder set' in result
        mock_create.assert_called_once_with('+15551234567', 'Test reminder')

    @patch('services.nudge_service.record_nudge_response')
    @patch('services.nudge_service.create_or_update_user')
    def test_done_for_followup(self, mock_update, mock_record):
        from services.nudge_service import handle_nudge_response
        result = handle_nudge_response('+15551234567', 'DONE', self._make_pending('reminder_followup'))
        assert 'Nice work' in result

    @patch('services.nudge_service.record_nudge_response')
    @patch('services.nudge_service.create_or_update_user')
    def test_snooze_response(self, mock_update, mock_record):
        from services.nudge_service import handle_nudge_response
        result = handle_nudge_response('+15551234567', 'SNOOZE 1d', self._make_pending('reminder_followup'))
        assert 'later' in result.lower()

    @patch('services.nudge_service.create_or_update_user')
    def test_long_message_clears_and_falls_through(self, mock_update):
        from services.nudge_service import handle_nudge_response
        result = handle_nudge_response('+15551234567', 'remind me to call mom tomorrow', self._make_pending())
        assert result is None  # Falls through to normal processing
        mock_update.assert_called_once()  # Pending cleared


# =====================================================
# KEYWORD HANDLER TESTS (via ConversationSimulator)
# =====================================================

class TestNudgeKeywordHandlers:
    """Test NUDGE ON/OFF/TIME/STATUS keyword handlers."""

    @pytest.mark.asyncio
    async def test_nudge_on(self, simulator, sms_capture, ai_mock, onboarded_user):
        """NUDGE ON should enable smart nudges."""
        phone = onboarded_user['phone']
        result = await simulator.send_message(phone, "NUDGE ON")
        assert 'nudge' in result['output'].lower() or 'enabled' in result['output'].lower()

    @pytest.mark.asyncio
    async def test_nudge_off(self, simulator, sms_capture, ai_mock, onboarded_user):
        """NUDGE OFF should disable smart nudges."""
        phone = onboarded_user['phone']
        await simulator.send_message(phone, "NUDGE ON")
        result = await simulator.send_message(phone, "NUDGE OFF")
        assert 'disabled' in result['output'].lower() or 'off' in result['output'].lower()

    @pytest.mark.asyncio
    async def test_nudge_status_when_off(self, simulator, sms_capture, ai_mock, onboarded_user):
        """NUDGE STATUS should show current settings."""
        phone = onboarded_user['phone']
        result = await simulator.send_message(phone, "NUDGE STATUS")
        assert 'off' in result['output'].lower()

    @pytest.mark.asyncio
    async def test_nudge_status_when_on(self, simulator, sms_capture, ai_mock, onboarded_user):
        """NUDGE STATUS should show enabled state after enabling."""
        phone = onboarded_user['phone']
        await simulator.send_message(phone, "NUDGE ON")
        result = await simulator.send_message(phone, "NUDGE STATUS")
        assert 'on' in result['output'].lower()

    @pytest.mark.asyncio
    async def test_nudge_time_set(self, simulator, sms_capture, ai_mock, onboarded_user):
        """NUDGE TIME 10AM should set the nudge time."""
        phone = onboarded_user['phone']
        result = await simulator.send_message(phone, "NUDGE TIME 10AM")
        assert '10:00 AM' in result['output']

    @pytest.mark.asyncio
    async def test_nudge_time_pm(self, simulator, sms_capture, ai_mock, onboarded_user):
        """NUDGE TIME 6PM should set the nudge time."""
        phone = onboarded_user['phone']
        result = await simulator.send_message(phone, "NUDGE TIME 6PM")
        assert '6:00 PM' in result['output']

    @pytest.mark.asyncio
    async def test_nudge_undo_after_enable(self, simulator, sms_capture, ai_mock, onboarded_user):
        """UNDO after NUDGE ON should revert to disabled."""
        phone = onboarded_user['phone']
        await simulator.send_message(phone, "NUDGE ON")
        result = await simulator.send_message(phone, "UNDO")
        assert 'nudge' in result['output'].lower() or 'off' in result['output'].lower()


# =====================================================
# CELERY TASK TESTS
# =====================================================

class TestSendSmartNudgesTask:
    """Test the Celery task for sending smart nudges."""

    @patch('tasks.reminder_tasks.send_nudge_to_user')
    @patch('tasks.reminder_tasks.generate_nudge')
    @patch('tasks.reminder_tasks.is_nudge_eligible', return_value=True)
    @patch('tasks.reminder_tasks.claim_user_for_smart_nudge', return_value=True)
    @patch('tasks.reminder_tasks.get_users_due_for_smart_nudge')
    def test_sends_nudge_to_eligible_users(self, mock_get_users, mock_claim, mock_eligible, mock_generate, mock_send):
        from tasks.reminder_tasks import send_smart_nudges

        mock_get_users.return_value = [{
            'phone_number': '+15551234567',
            'timezone': 'America/New_York',
            'first_name': 'Brad',
            'premium_status': 'premium',
        }]
        mock_generate.return_value = {
            'nudge_type': 'weekly_reflection',
            'nudge_text': 'Great week!',
            'confidence': 80,
        }
        mock_send.return_value = True

        result = send_smart_nudges()
        assert result['sent'] == 1
        mock_generate.assert_called_once()
        mock_send.assert_called_once()

    @patch('tasks.reminder_tasks.get_users_due_for_smart_nudge')
    def test_no_users_due(self, mock_get_users):
        from tasks.reminder_tasks import send_smart_nudges
        mock_get_users.return_value = []
        result = send_smart_nudges()
        assert result['sent'] == 0

    @patch('tasks.reminder_tasks.generate_nudge', return_value=None)
    @patch('tasks.reminder_tasks.is_nudge_eligible', return_value=True)
    @patch('tasks.reminder_tasks.claim_user_for_smart_nudge', return_value=True)
    @patch('tasks.reminder_tasks.get_users_due_for_smart_nudge')
    def test_no_nudge_generated(self, mock_get_users, mock_claim, mock_eligible, mock_generate):
        from tasks.reminder_tasks import send_smart_nudges

        mock_get_users.return_value = [{
            'phone_number': '+15551234567',
            'timezone': 'America/New_York',
            'first_name': 'Brad',
            'premium_status': 'premium',
        }]

        result = send_smart_nudges()
        assert result['sent'] == 0

    @patch('tasks.reminder_tasks.is_nudge_eligible', return_value=False)
    @patch('tasks.reminder_tasks.get_users_due_for_smart_nudge')
    def test_free_tier_skipped_on_weekday(self, mock_get_users, mock_eligible):
        from tasks.reminder_tasks import send_smart_nudges

        mock_get_users.return_value = [{
            'phone_number': '+15551234567',
            'timezone': 'America/New_York',
            'first_name': 'Brad',
            'premium_status': 'free',
        }]

        result = send_smart_nudges()
        assert result['sent'] == 0


# =====================================================
# CONFIG TESTS
# =====================================================

class TestNudgeConfig:
    """Test nudge configuration constants."""

    def test_nudge_constants_exist(self):
        from config import NUDGE_DEFAULT_TIME, NUDGE_MAX_TOKENS, NUDGE_TEMPERATURE, NUDGE_CONFIDENCE_THRESHOLD, NUDGE_MAX_CHARS
        assert NUDGE_DEFAULT_TIME == "09:00"
        assert NUDGE_MAX_TOKENS == 300
        assert NUDGE_TEMPERATURE == 0.4
        assert NUDGE_CONFIDENCE_THRESHOLD == 50
        assert NUDGE_MAX_CHARS == 280


# =====================================================
# USER MODEL TESTS
# =====================================================

class TestUserNudgeFields:
    """Test that nudge fields are properly whitelisted."""

    def test_nudge_fields_in_allowed_fields(self):
        from models.user import ALLOWED_USER_FIELDS
        assert 'smart_nudges_enabled' in ALLOWED_USER_FIELDS
        assert 'smart_nudge_time' in ALLOWED_USER_FIELDS
        assert 'smart_nudge_last_sent' in ALLOWED_USER_FIELDS
        assert 'pending_nudge_response' in ALLOWED_USER_FIELDS
