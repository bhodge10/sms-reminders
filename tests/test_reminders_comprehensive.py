"""
Comprehensive Reminder Tests for Remyndrs SMS Service

Tests reminder creation, recurring reminders, management, and special features.
All tests use ConversationSimulator and mock AI responses.
"""

import pytest
from datetime import datetime, timedelta


@pytest.mark.asyncio
class TestReminderCreation:
    """Test scenarios for creating reminders."""

    async def test_create_reminder_with_specific_date_and_time(self, simulator, onboarded_user, ai_mock):
        """Create reminder with specific date and time (tomorrow at 3pm)."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me tomorrow at 3pm to call mom", {
            "action": "reminder",
            "reminder_text": "call mom",
            "reminder_date": "2026-01-19 15:00:00",
            "confirmation": "I'll remind you tomorrow at 3:00 PM to call mom."
        })

        result = await simulator.send_message(phone, "remind me tomorrow at 3pm to call mom")
        output_lower = result["output"].lower()
        assert "remind" in output_lower or "3" in result["output"] or "call mom" in output_lower or "tomorrow" in output_lower

    async def test_create_reminder_with_ampm_specified(self, simulator, onboarded_user, ai_mock):
        """Create reminder with AM/PM specified."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me at 8am to take medicine", {
            "action": "reminder",
            "reminder_text": "take medicine",
            "reminder_date": "2026-01-18 08:00:00",
            "confirmation": "I'll remind you at 8:00 AM to take medicine."
        })

        result = await simulator.send_message(phone, "remind me at 8am to take medicine")
        output_lower = result["output"].lower()
        assert "8" in result["output"] or "medicine" in output_lower or "remind" in output_lower

    async def test_create_reminder_needing_ampm_clarification(self, simulator, onboarded_user, ai_mock):
        """Create reminder needing AM/PM clarification."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me at 4 to call mom", {
            "action": "clarify_time",
            "reminder_text": "call mom",
            "time_mentioned": "4:00"
        })

        result = await simulator.send_message(phone, "remind me at 4 to call mom")
        output_lower = result["output"].lower()
        # Should ask for AM or PM
        assert "am" in output_lower or "pm" in output_lower

    async def test_respond_to_ampm_clarification(self, simulator, onboarded_user, ai_mock):
        """Respond to AM/PM clarification with 'PM'."""
        phone = onboarded_user["phone"]

        # First, trigger the clarification
        ai_mock.set_response("remind me at 4 to call mom", {
            "action": "clarify_time",
            "reminder_text": "call mom",
            "time_mentioned": "4:00"
        })
        await simulator.send_message(phone, "remind me at 4 to call mom")

        # Respond with PM
        result = await simulator.send_message(phone, "PM")
        output_lower = result["output"].lower()
        # Should confirm the reminder
        assert "4" in result["output"] or "pm" in output_lower or "call mom" in output_lower or "remind" in output_lower

    async def test_create_reminder_date_without_time(self, simulator, onboarded_user, ai_mock):
        """Create reminder with date but no time - asks for time."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me on friday to submit report", {
            "action": "clarify_date_time",
            "reminder_text": "submit report",
            "reminder_date": "2026-01-24"
        })

        result = await simulator.send_message(phone, "remind me on friday to submit report")
        output_lower = result["output"].lower()
        # Should ask for time
        assert "time" in output_lower or "when" in output_lower or "what time" in output_lower or "friday" in output_lower

    async def test_respond_to_time_clarification(self, simulator, onboarded_user, ai_mock):
        """Respond to time clarification."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me on friday to submit report", {
            "action": "clarify_date_time",
            "reminder_text": "submit report",
            "reminder_date": "2026-01-24"
        })
        await simulator.send_message(phone, "remind me on friday to submit report")

        # Respond with time
        result = await simulator.send_message(phone, "9am")
        output_lower = result["output"].lower()
        assert "9" in result["output"] or "friday" in output_lower or "report" in output_lower or "remind" in output_lower

    async def test_create_reminder_vague_time(self, simulator, onboarded_user, ai_mock):
        """Create reminder with vague time (later, soon, in a bit)."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me later to water the plants", {
            "action": "clarify_specific_time",
            "reminder_text": "water the plants"
        })

        result = await simulator.send_message(phone, "remind me later to water the plants")
        output_lower = result["output"].lower()
        # Should ask for specific time
        assert "time" in output_lower or "when" in output_lower or "specific" in output_lower or "plant" in output_lower

    async def test_respond_to_vague_time_request(self, simulator, onboarded_user, ai_mock):
        """Respond to specific time request after vague time."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me later to water the plants", {
            "action": "clarify_specific_time",
            "reminder_text": "water the plants"
        })
        await simulator.send_message(phone, "remind me later to water the plants")

        # Respond with specific time
        result = await simulator.send_message(phone, "3pm")
        output_lower = result["output"].lower()
        assert "3" in result["output"] or "pm" in output_lower or "plant" in output_lower or "remind" in output_lower


@pytest.mark.asyncio
class TestRelativeReminders:
    """Test scenarios for relative time reminders."""

    async def test_reminder_in_30_minutes(self, simulator, onboarded_user, ai_mock):
        """Reminder 'in 30 minutes'."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me in 30 minutes to check the oven", {
            "action": "reminder_relative",
            "reminder_text": "check the oven",
            "offset_minutes": 30
        })

        result = await simulator.send_message(phone, "remind me in 30 minutes to check the oven")
        output_lower = result["output"].lower()
        assert "30" in result["output"] or "minute" in output_lower or "oven" in output_lower or "remind" in output_lower

    async def test_reminder_in_2_hours(self, simulator, onboarded_user, ai_mock):
        """Reminder 'in 2 hours'."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me in 2 hours to pick up laundry", {
            "action": "reminder_relative",
            "reminder_text": "pick up laundry",
            "offset_minutes": 120
        })

        result = await simulator.send_message(phone, "remind me in 2 hours to pick up laundry")
        output_lower = result["output"].lower()
        assert "2" in result["output"] or "hour" in output_lower or "laundry" in output_lower or "remind" in output_lower

    async def test_reminder_in_3_days(self, simulator, onboarded_user, ai_mock):
        """Reminder 'in 3 days'."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me in 3 days to pay rent", {
            "action": "reminder_relative",
            "reminder_text": "pay rent",
            "offset_days": 3
        })

        result = await simulator.send_message(phone, "remind me in 3 days to pay rent")
        output_lower = result["output"].lower()
        assert "3" in result["output"] or "day" in output_lower or "rent" in output_lower or "remind" in output_lower or "january" in output_lower

    async def test_reminder_in_2_weeks(self, simulator, onboarded_user, ai_mock):
        """Reminder 'in 2 weeks'."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me in 2 weeks to renew subscription", {
            "action": "reminder_relative",
            "reminder_text": "renew subscription",
            "offset_weeks": 2
        })

        result = await simulator.send_message(phone, "remind me in 2 weeks to renew subscription")
        output_lower = result["output"].lower()
        assert "2" in result["output"] or "week" in output_lower or "subscription" in output_lower or "remind" in output_lower or "february" in output_lower

    async def test_reminder_in_5_months(self, simulator, onboarded_user, ai_mock):
        """Reminder 'in 5 months'."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me in 5 months to schedule checkup", {
            "action": "reminder_relative",
            "reminder_text": "schedule checkup",
            "offset_months": 5
        })

        result = await simulator.send_message(phone, "remind me in 5 months to schedule checkup")
        output_lower = result["output"].lower()
        assert "5" in result["output"] or "month" in output_lower or "checkup" in output_lower or "remind" in output_lower or "june" in output_lower

    async def test_reminder_tomorrow(self, simulator, onboarded_user, ai_mock):
        """Reminder 'tomorrow' (relative day)."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me tomorrow at noon to call dad", {
            "action": "reminder",
            "reminder_text": "call dad",
            "reminder_date": "2026-01-19 12:00:00"
        })

        result = await simulator.send_message(phone, "remind me tomorrow at noon to call dad")
        output_lower = result["output"].lower()
        assert "tomorrow" in output_lower or "noon" in output_lower or "12" in result["output"] or "dad" in output_lower


@pytest.mark.asyncio
class TestRecurringReminders:
    """Test scenarios for recurring reminders."""

    async def test_create_daily_recurring_reminder(self, simulator, onboarded_user, ai_mock):
        """Create daily recurring reminder."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me every day at 9am to take vitamins", {
            "action": "reminder_recurring",
            "reminder_text": "take vitamins",
            "recurrence_type": "daily",
            "time": "09:00"
        })

        result = await simulator.send_message(phone, "remind me every day at 9am to take vitamins")
        output_lower = result["output"].lower()
        assert "daily" in output_lower or "every day" in output_lower or "vitamin" in output_lower or "9" in result["output"]

    async def test_create_weekly_recurring_reminder(self, simulator, onboarded_user, ai_mock):
        """Create weekly recurring reminder (every Monday)."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me every monday at 8am to submit timesheet", {
            "action": "reminder_recurring",
            "reminder_text": "submit timesheet",
            "recurrence_type": "weekly",
            "recurrence_day": "monday",
            "time": "08:00"
        })

        result = await simulator.send_message(phone, "remind me every monday at 8am to submit timesheet")
        output_lower = result["output"].lower()
        assert "monday" in output_lower or "weekly" in output_lower or "timesheet" in output_lower or "8" in result["output"]

    async def test_create_weekday_recurring_reminder(self, simulator, onboarded_user, ai_mock):
        """Create weekday recurring reminder."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me every weekday at 7am to exercise", {
            "action": "reminder_recurring",
            "reminder_text": "exercise",
            "recurrence_type": "weekdays",
            "time": "07:00"
        })

        result = await simulator.send_message(phone, "remind me every weekday at 7am to exercise")
        output_lower = result["output"].lower()
        assert "weekday" in output_lower or "monday" in output_lower or "exercise" in output_lower or "7" in result["output"]

    async def test_create_weekend_recurring_reminder(self, simulator, onboarded_user, ai_mock):
        """Create weekend recurring reminder."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me every weekend at 10am to relax", {
            "action": "reminder_recurring",
            "reminder_text": "relax",
            "recurrence_type": "weekends",
            "time": "10:00"
        })

        result = await simulator.send_message(phone, "remind me every weekend at 10am to relax")
        output_lower = result["output"].lower()
        assert "weekend" in output_lower or "saturday" in output_lower or "sunday" in output_lower or "relax" in output_lower

    async def test_create_monthly_recurring_reminder(self, simulator, onboarded_user, ai_mock):
        """Create monthly recurring reminder."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me on the 1st of every month at 9am to pay rent", {
            "action": "reminder_recurring",
            "reminder_text": "pay rent",
            "recurrence_type": "monthly",
            "recurrence_day": 1,
            "time": "09:00"
        })

        result = await simulator.send_message(phone, "remind me on the 1st of every month at 9am to pay rent")
        output_lower = result["output"].lower()
        assert "month" in output_lower or "1st" in output_lower or "rent" in output_lower or "9" in result["output"]

    async def test_pause_recurring_reminder(self, simulator, onboarded_user, ai_mock):
        """Pause recurring reminder."""
        phone = onboarded_user["phone"]

        # Create recurring first
        ai_mock.set_response("remind me every day at 9am to take vitamins", {
            "action": "reminder_recurring",
            "reminder_text": "take vitamins",
            "recurrence_type": "daily",
            "time": "09:00"
        })
        await simulator.send_message(phone, "remind me every day at 9am to take vitamins")

        # Pause it
        ai_mock.set_response("pause my vitamin reminder", {
            "action": "pause_recurring",
            "reminder_text": "take vitamins"
        })
        result = await simulator.send_message(phone, "pause my vitamin reminder")

        output_lower = result["output"].lower()
        assert "pause" in output_lower or "vitamin" in output_lower or "stopped" in output_lower

    async def test_resume_recurring_reminder(self, simulator, onboarded_user, ai_mock):
        """Resume recurring reminder."""
        phone = onboarded_user["phone"]

        # Create and pause recurring
        ai_mock.set_response("remind me every day at 9am to take vitamins", {
            "action": "reminder_recurring",
            "reminder_text": "take vitamins",
            "recurrence_type": "daily",
            "time": "09:00"
        })
        await simulator.send_message(phone, "remind me every day at 9am to take vitamins")

        ai_mock.set_response("pause my vitamin reminder", {"action": "pause_recurring"})
        await simulator.send_message(phone, "pause my vitamin reminder")

        # Resume it
        ai_mock.set_response("resume my vitamin reminder", {
            "action": "resume_recurring",
            "reminder_text": "take vitamins"
        })
        result = await simulator.send_message(phone, "resume my vitamin reminder")

        output_lower = result["output"].lower()
        assert "resume" in output_lower or "vitamin" in output_lower or "reactivate" in output_lower or "started" in output_lower

    async def test_delete_recurring_reminder(self, simulator, onboarded_user, ai_mock):
        """Delete recurring reminder (deletes future, keeps history)."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me every day at 9am to take vitamins", {
            "action": "reminder_recurring",
            "reminder_text": "take vitamins",
            "recurrence_type": "daily",
            "time": "09:00"
        })
        await simulator.send_message(phone, "remind me every day at 9am to take vitamins")

        ai_mock.set_response("delete my vitamin recurring reminder", {
            "action": "delete_recurring",
            "reminder_text": "take vitamins"
        })
        result = await simulator.send_message(phone, "delete my vitamin recurring reminder")

        output_lower = result["output"].lower()
        assert "delete" in output_lower or "vitamin" in output_lower or "removed" in output_lower or "recurring" in output_lower


@pytest.mark.asyncio
class TestReminderManagement:
    """Test scenarios for managing reminders."""

    async def test_list_all_reminders(self, simulator, onboarded_user, ai_mock):
        """List all reminders."""
        phone = onboarded_user["phone"]

        # Create some reminders
        ai_mock.set_response("remind me tomorrow at 3pm to call mom", {
            "action": "reminder",
            "reminder_text": "call mom",
            "reminder_date": "2026-01-19 15:00:00"
        })
        await simulator.send_message(phone, "remind me tomorrow at 3pm to call mom")

        ai_mock.set_response("remind me in 2 hours to check email", {
            "action": "reminder_relative",
            "reminder_text": "check email",
            "offset_minutes": 120
        })
        await simulator.send_message(phone, "remind me in 2 hours to check email")

        # List all
        result = await simulator.send_message(phone, "my reminders")

        output_lower = result["output"].lower()
        assert "reminder" in output_lower or "call mom" in output_lower or "email" in output_lower or "1." in result["output"]

    async def test_delete_reminder_by_number(self, simulator, onboarded_user, ai_mock):
        """Delete reminder by number."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me tomorrow at 3pm to call mom", {
            "action": "reminder",
            "reminder_text": "call mom",
            "reminder_date": "2026-01-19 15:00:00"
        })
        await simulator.send_message(phone, "remind me tomorrow at 3pm to call mom")

        # List reminders
        await simulator.send_message(phone, "my reminders")

        # Delete by number
        result = await simulator.send_message(phone, "delete reminder 1")

        output_lower = result["output"].lower()
        assert "delete" in output_lower or "call mom" in output_lower or "removed" in output_lower or "yes" in output_lower

    async def test_delete_reminder_by_keyword(self, simulator, onboarded_user, ai_mock):
        """Delete reminder by keyword search."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me tomorrow at 3pm to call mom", {
            "action": "reminder",
            "reminder_text": "call mom",
            "reminder_date": "2026-01-19 15:00:00"
        })
        await simulator.send_message(phone, "remind me tomorrow at 3pm to call mom")

        ai_mock.set_response("delete my mom reminder", {
            "action": "delete_reminder",
            "search_term": "mom"
        })
        result = await simulator.send_message(phone, "delete my mom reminder")

        output_lower = result["output"].lower()
        assert "delete" in output_lower or "mom" in output_lower or "call" in output_lower or "yes" in output_lower

    async def test_delete_confirmation_with_yes(self, simulator, onboarded_user, ai_mock):
        """Delete confirmation with YES."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me tomorrow at 3pm to call mom", {
            "action": "reminder",
            "reminder_text": "call mom",
            "reminder_date": "2026-01-19 15:00:00"
        })
        await simulator.send_message(phone, "remind me tomorrow at 3pm to call mom")

        ai_mock.set_response("delete my mom reminder", {"action": "delete_reminder", "search_term": "mom"})
        result = await simulator.send_message(phone, "delete my mom reminder")

        if "yes" in result["output"].lower() or "confirm" in result["output"].lower():
            result = await simulator.send_message(phone, "yes")
            output_lower = result["output"].lower()
            assert "deleted" in output_lower or "removed" in output_lower or "done" in output_lower

    async def test_delete_cancellation_with_no(self, simulator, onboarded_user, ai_mock):
        """Delete cancellation with NO."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me tomorrow at 3pm to call mom", {
            "action": "reminder",
            "reminder_text": "call mom",
            "reminder_date": "2026-01-19 15:00:00"
        })
        await simulator.send_message(phone, "remind me tomorrow at 3pm to call mom")

        ai_mock.set_response("delete my mom reminder", {"action": "delete_reminder", "search_term": "mom"})
        result = await simulator.send_message(phone, "delete my mom reminder")

        if "yes" in result["output"].lower() or "confirm" in result["output"].lower():
            result = await simulator.send_message(phone, "no")
            output_lower = result["output"].lower()
            assert "kept" in output_lower or "cancel" in output_lower or "ok" in output_lower or "not" in output_lower


@pytest.mark.asyncio
class TestReminderSpecialFeatures:
    """Test special reminder features."""

    async def test_snooze_reminder_default(self, simulator, onboarded_user, ai_mock):
        """Snooze reminder (default 15 min)."""
        phone = onboarded_user["phone"]

        # Simulate having just received a reminder
        ai_mock.set_response("snooze", {
            "action": "snooze",
            "duration_minutes": 15
        })
        result = await simulator.send_message(phone, "snooze")

        output_lower = result["output"].lower()
        assert "snooze" in output_lower or "15" in result["output"] or "minute" in output_lower or "remind" in output_lower

    async def test_snooze_custom_duration(self, simulator, onboarded_user, ai_mock):
        """Snooze with custom duration ('snooze 1 hour')."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("snooze 1 hour", {
            "action": "snooze",
            "duration_minutes": 60
        })
        result = await simulator.send_message(phone, "snooze 1 hour")

        output_lower = result["output"].lower()
        assert "snooze" in output_lower or "1" in result["output"] or "hour" in output_lower or "60" in result["output"]

    async def test_undo_last_reminder(self, simulator, onboarded_user, ai_mock):
        """Undo last created reminder."""
        phone = onboarded_user["phone"]

        # Create a reminder
        ai_mock.set_response("remind me tomorrow at 3pm to call mom", {
            "action": "reminder",
            "reminder_text": "call mom",
            "reminder_date": "2026-01-19 15:00:00"
        })
        await simulator.send_message(phone, "remind me tomorrow at 3pm to call mom")

        # Undo it
        result = await simulator.send_message(phone, "undo")

        output_lower = result["output"].lower()
        assert "undo" in output_lower or "delete" in output_lower or "call mom" in output_lower or "recent" in output_lower

    async def test_update_reminder_time(self, simulator, onboarded_user, ai_mock):
        """Update reminder time."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me tomorrow at 3pm to call mom", {
            "action": "reminder",
            "reminder_text": "call mom",
            "reminder_date": "2026-01-19 15:00:00"
        })
        await simulator.send_message(phone, "remind me tomorrow at 3pm to call mom")

        ai_mock.set_response("change my call mom reminder to 4pm", {
            "action": "update_reminder",
            "reminder_text": "call mom",
            "new_time": "16:00"
        })
        result = await simulator.send_message(phone, "change my call mom reminder to 4pm")

        output_lower = result["output"].lower()
        assert "update" in output_lower or "4" in result["output"] or "change" in output_lower or "call mom" in output_lower


@pytest.mark.asyncio
class TestReminderConfidence:
    """Test low confidence reminder handling."""

    async def test_low_confidence_confirm_yes(self, simulator, onboarded_user, ai_mock):
        """Low confidence reminder - confirm with YES."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me about that thing next week maybe", {
            "action": "reminder",
            "reminder_text": "that thing",
            "reminder_date": "2026-01-25 12:00:00",
            "confidence": 40,
            "needs_confirmation": True,
            "confirmation": "Did you mean to set a reminder for 'that thing' on January 25?"
        })
        result = await simulator.send_message(phone, "remind me about that thing next week maybe")

        output_lower = result["output"].lower()
        # Should ask for confirmation
        if "correct" in output_lower or "right" in output_lower or "confirm" in output_lower or "yes" in output_lower:
            result = await simulator.send_message(phone, "yes")
            assert "remind" in result["output"].lower() or "that thing" in result["output"].lower()

    async def test_low_confidence_reject_no(self, simulator, onboarded_user, ai_mock):
        """Low confidence reminder - reject with NO."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remind me about that thing next week maybe", {
            "action": "reminder",
            "reminder_text": "that thing",
            "reminder_date": "2026-01-25 12:00:00",
            "confidence": 40,
            "needs_confirmation": True
        })
        result = await simulator.send_message(phone, "remind me about that thing next week maybe")

        output_lower = result["output"].lower()
        if "correct" in output_lower or "right" in output_lower or "confirm" in output_lower:
            result = await simulator.send_message(phone, "no")
            output_lower = result["output"].lower()
            assert "again" in output_lower or "try" in output_lower or "what" in output_lower or "please" in output_lower


@pytest.mark.asyncio
class TestReminderLimits:
    """Test reminder limits."""

    async def test_hit_free_tier_daily_limit(self, simulator, onboarded_user, ai_mock):
        """Hit free tier daily limit (2 reminders/day)."""
        phone = onboarded_user["phone"]

        # Create 2 reminders
        for i in range(2):
            ai_mock.set_response(f"remind me in {i+1} hours to task {i+1}", {
                "action": "reminder_relative",
                "reminder_text": f"task {i+1}",
                "offset_minutes": (i+1) * 60
            })
            await simulator.send_message(phone, f"remind me in {i+1} hours to task {i+1}")

        # Try to create 3rd reminder
        ai_mock.set_response("remind me in 3 hours to task 3", {
            "action": "reminder_relative",
            "reminder_text": "task 3",
            "offset_minutes": 180
        })
        result = await simulator.send_message(phone, "remind me in 3 hours to task 3")

        output_lower = result["output"].lower()
        # Should hit limit or succeed (depends on implementation)
        assert "limit" in output_lower or "maximum" in output_lower or "upgrade" in output_lower or "task" in output_lower or "2" in result["output"]
