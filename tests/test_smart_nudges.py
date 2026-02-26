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

    @patch('services.nudge_service.send_nudge_to_user')
    @patch('services.nudge_service.generate_nudge')
    @patch('services.nudge_service.is_nudge_eligible', return_value=True)
    @patch('models.user.claim_user_for_smart_nudge', return_value=True)
    @patch('models.user.get_users_due_for_smart_nudge')
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

    @patch('models.user.get_users_due_for_smart_nudge')
    def test_no_users_due(self, mock_get_users):
        from tasks.reminder_tasks import send_smart_nudges
        mock_get_users.return_value = []
        result = send_smart_nudges()
        assert result['sent'] == 0

    @patch('services.nudge_service.generate_nudge', return_value=None)
    @patch('services.nudge_service.is_nudge_eligible', return_value=True)
    @patch('models.user.claim_user_for_smart_nudge', return_value=True)
    @patch('models.user.get_users_due_for_smart_nudge')
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

    @patch('services.nudge_service.is_nudge_eligible', return_value=False)
    @patch('models.user.get_users_due_for_smart_nudge')
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

    def test_combined_nudge_max_chars_exists(self):
        from config import COMBINED_NUDGE_MAX_CHARS
        assert COMBINED_NUDGE_MAX_CHARS == 1500


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


# =====================================================
# COMBINED SUMMARY + NUDGE TESTS
# =====================================================

class TestFormatCompactSummary:
    """Test the compact summary formatter used in combined nudge messages."""

    def test_formats_reminders(self):
        import pytz
        from datetime import datetime, date
        from tasks.reminder_tasks import format_compact_summary

        tz = pytz.timezone('America/New_York')
        today = date(2026, 2, 23)
        utc_dt = datetime(2026, 2, 23, 19, 0, 0, tzinfo=pytz.UTC)  # 2:00 PM ET
        reminders = [(1, 'Call dentist', utc_dt), (2, 'Team meeting', utc_dt)]

        result = format_compact_summary(reminders, today, tz)
        assert "Today's reminders" in result
        assert 'Monday, February 23' in result
        assert '1.' in result
        assert '2.' in result
        assert 'Call dentist' in result
        assert 'Team meeting' in result

    def test_empty_reminders_returns_empty_string(self):
        import pytz
        from datetime import date
        from tasks.reminder_tasks import format_compact_summary

        tz = pytz.timezone('America/New_York')
        today = date(2026, 2, 23)
        result = format_compact_summary([], today, tz)
        assert result == ""


class TestCombinedSummaryNudge:
    """Test that send_smart_nudges combines reminders + nudge into one message."""

    def _make_nudge_data(self, nudge_text='Great insight!'):
        return {
            'nudge_type': 'weekly_reflection',
            'nudge_text': nudge_text,
            'confidence': 80,
            'suggested_reminder_text': None,
            'related_reminder_id': None,
            'raw_response': '{}',
        }

    @patch('models.user.mark_daily_summary_sent')
    @patch('services.nudge_service.send_nudge_to_user', return_value=True)
    @patch('services.nudge_service.generate_nudge')
    @patch('models.reminder.get_reminders_for_date')
    @patch('services.nudge_service.is_nudge_eligible', return_value=True)
    @patch('models.user.claim_user_for_smart_nudge', return_value=True)
    @patch('models.user.get_users_due_for_smart_nudge')
    def test_nudge_with_reminders_combines_message(
        self, mock_get_users, mock_claim, mock_eligible, mock_reminders,
        mock_generate, mock_send_nudge, mock_mark_summary
    ):
        """When both reminders and nudge exist, sends combined message."""
        from tasks.reminder_tasks import send_smart_nudges
        import pytz
        from datetime import datetime

        mock_get_users.return_value = [{
            'phone_number': '+15551234567',
            'timezone': 'America/New_York',
            'first_name': 'Brad',
            'premium_status': 'premium',
        }]
        utc_dt = datetime(2026, 2, 23, 19, 0, 0, tzinfo=pytz.UTC)
        mock_reminders.return_value = [(1, 'Call dentist', utc_dt)]
        mock_generate.return_value = self._make_nudge_data()

        result = send_smart_nudges()
        assert result['sent'] == 1
        mock_send_nudge.assert_called_once()
        # The nudge_data passed to send_nudge_to_user should have combined text
        sent_data = mock_send_nudge.call_args[0][1]
        assert "Today's reminders" in sent_data['nudge_text']
        assert 'Great insight!' in sent_data['nudge_text']
        # daily_summary_last_sent should be marked
        mock_mark_summary.assert_called_once_with('+15551234567')

    @patch('services.nudge_service.send_nudge_to_user', return_value=True)
    @patch('services.nudge_service.generate_nudge')
    @patch('models.reminder.get_reminders_for_date')
    @patch('services.nudge_service.is_nudge_eligible', return_value=True)
    @patch('models.user.claim_user_for_smart_nudge', return_value=True)
    @patch('models.user.get_users_due_for_smart_nudge')
    def test_nudge_without_reminders_sends_nudge_only(
        self, mock_get_users, mock_claim, mock_eligible, mock_reminders,
        mock_generate, mock_send_nudge
    ):
        """When no reminders but nudge exists, sends just the nudge."""
        from tasks.reminder_tasks import send_smart_nudges

        mock_get_users.return_value = [{
            'phone_number': '+15551234567',
            'timezone': 'America/New_York',
            'first_name': 'Brad',
            'premium_status': 'premium',
        }]
        mock_reminders.return_value = []
        mock_generate.return_value = self._make_nudge_data()

        result = send_smart_nudges()
        assert result['sent'] == 1
        sent_data = mock_send_nudge.call_args[0][1]
        assert sent_data['nudge_text'] == 'Great insight!'

    @patch('models.user.mark_daily_summary_sent')
    @patch('services.sms_service.send_sms')
    @patch('services.nudge_service.generate_nudge', return_value=None)
    @patch('models.reminder.get_reminders_for_date')
    @patch('services.nudge_service.is_nudge_eligible', return_value=True)
    @patch('models.user.claim_user_for_smart_nudge', return_value=True)
    @patch('models.user.get_users_due_for_smart_nudge')
    def test_no_nudge_but_reminders_sends_compact_summary(
        self, mock_get_users, mock_claim, mock_eligible, mock_reminders,
        mock_generate, mock_send_sms, mock_mark_summary
    ):
        """When AI returns no nudge but reminders exist, sends compact summary."""
        from tasks.reminder_tasks import send_smart_nudges
        import pytz
        from datetime import datetime

        mock_get_users.return_value = [{
            'phone_number': '+15551234567',
            'timezone': 'America/New_York',
            'first_name': 'Brad',
            'premium_status': 'premium',
        }]
        utc_dt = datetime(2026, 2, 23, 19, 0, 0, tzinfo=pytz.UTC)
        mock_reminders.return_value = [(1, 'Call dentist', utc_dt)]

        result = send_smart_nudges()
        assert result['sent'] == 1
        # Should have called send_sms directly with compact summary
        mock_send_sms.assert_called_once()
        sent_message = mock_send_sms.call_args[0][1]
        assert "Today's reminders" in sent_message
        assert 'Call dentist' in sent_message
        mock_mark_summary.assert_called_once()

    @patch('services.sms_service.send_sms')
    @patch('services.nudge_service.generate_nudge', return_value=None)
    @patch('models.reminder.get_reminders_for_date')
    @patch('services.nudge_service.is_nudge_eligible', return_value=True)
    @patch('models.user.claim_user_for_smart_nudge', return_value=True)
    @patch('models.user.get_users_due_for_smart_nudge')
    def test_no_nudge_no_reminders_sends_nothing(
        self, mock_get_users, mock_claim, mock_eligible, mock_reminders,
        mock_generate, mock_send_sms
    ):
        """When neither nudge nor reminders, nothing is sent."""
        from tasks.reminder_tasks import send_smart_nudges

        mock_get_users.return_value = [{
            'phone_number': '+15551234567',
            'timezone': 'America/New_York',
            'first_name': 'Brad',
            'premium_status': 'premium',
        }]
        mock_reminders.return_value = []

        result = send_smart_nudges()
        assert result['sent'] == 0
        mock_send_sms.assert_not_called()

    @patch('models.user.mark_daily_summary_sent')
    @patch('services.nudge_service.send_nudge_to_user', return_value=True)
    @patch('services.nudge_service.generate_nudge')
    @patch('models.reminder.get_reminders_for_date')
    @patch('services.nudge_service.is_nudge_eligible', return_value=True)
    @patch('models.user.claim_user_for_smart_nudge', return_value=True)
    @patch('models.user.get_users_due_for_smart_nudge')
    def test_combined_message_truncated_at_limit(
        self, mock_get_users, mock_claim, mock_eligible, mock_reminders,
        mock_generate, mock_send_nudge, mock_mark_summary
    ):
        """Combined message is truncated at COMBINED_NUDGE_MAX_CHARS."""
        from tasks.reminder_tasks import send_smart_nudges
        from config import COMBINED_NUDGE_MAX_CHARS
        import pytz
        from datetime import datetime

        mock_get_users.return_value = [{
            'phone_number': '+15551234567',
            'timezone': 'America/New_York',
            'first_name': 'Brad',
            'premium_status': 'premium',
        }]
        utc_dt = datetime(2026, 2, 23, 19, 0, 0, tzinfo=pytz.UTC)
        # Create many reminders to make a long summary
        mock_reminders.return_value = [(i, f'Reminder {i} with a long text to fill space', utc_dt) for i in range(50)]
        mock_generate.return_value = self._make_nudge_data('A' * 500)

        result = send_smart_nudges()
        assert result['sent'] == 1
        sent_data = mock_send_nudge.call_args[0][1]
        assert len(sent_data['nudge_text']) <= COMBINED_NUDGE_MAX_CHARS

    @patch('models.user.get_users_due_for_daily_summary')
    def test_daily_summary_skips_nudge_enabled_users(self, mock_get_users):
        """send_daily_summaries skips users with smart_nudges_enabled=True."""
        from tasks.reminder_tasks import send_daily_summaries

        mock_get_users.return_value = [{
            'phone_number': '+15551234567',
            'timezone': 'America/New_York',
            'first_name': 'Brad',
            'smart_nudges_enabled': True,
        }]

        result = send_daily_summaries()
        assert result['sent'] == 0

    @patch('models.user.get_users_due_for_daily_summary')
    @patch('models.user.claim_user_for_daily_summary', return_value=True)
    @patch('models.reminder.get_reminders_for_date', return_value=[])
    @patch('tasks.reminder_tasks.send_sms')
    def test_daily_summary_sends_to_non_nudge_users(
        self, mock_send_sms, mock_reminders, mock_claim, mock_get_users
    ):
        """send_daily_summaries still works for users without nudges."""
        from tasks.reminder_tasks import send_daily_summaries

        mock_get_users.return_value = [{
            'phone_number': '+15551234567',
            'timezone': 'America/New_York',
            'first_name': 'Brad',
            'smart_nudges_enabled': False,
        }]

        result = send_daily_summaries()
        assert result['sent'] == 1
        mock_send_sms.assert_called_once()

    def test_nudge_prompt_contains_rule_9(self):
        """build_nudge_prompt includes rule about not listing reminders."""
        from services.nudge_service import build_nudge_prompt
        user_data = {
            'current_date': '2026-02-23', 'current_day': 'Monday',
            'memories': [{'text': 'Test', 'created_at': '2026-01-01'}],
            'upcoming_reminders': [], 'recently_completed_reminders': [],
            'lists': [], 'recent_nudges': [],
        }
        prompt = build_nudge_prompt(user_data, 'User', 'premium')
        assert 'DO NOT list or summarize upcoming reminders' in prompt
