"""
Formatting Utilities
Helper functions for formatting text and data
"""

def get_help_text():
    """Return help guide for users"""
    return """How to Use This Service

STORING MEMORIES:
Just text naturally!
- "My Honda Accord is a 2018, VIN ABC123"
- "Dentist is Dr. Smith, 555-1234"

FINDING MEMORIES:
Ask naturally:
- "What's my VIN?"
- "What's my dentist's number?"

SETTING REMINDERS:
- "Remind me at 9pm to take meds"
- "Remind me tomorrow at 2pm to call mom"
- "Remind me in 30 minutes to check laundry"

MANAGING LISTS:
- "Create a grocery list"
- "Add milk to my grocery list"
- "Show my grocery list"
- "Check off milk"
- "Remove eggs from grocery list"

COMMANDS:
- LIST ALL - View all your memories
- LIST REMINDERS - View all reminders
- MY LISTS - View all your lists
- DELETE ALL - Clear all data (asks confirmation)
- RESET ACCOUNT - Start over from scratch
- INFO - Show this guide

TIPS:
- For reminders, always include AM or PM
- I understand natural language - just talk!
- Your timezone is set from your ZIP code

Need more help? Just ask!"""

def get_onboarding_prompt(step):
    """Get the appropriate prompt for the current onboarding step"""
    prompts = {
        1: "What's your first name?",
        2: "What's your last name?",
        3: "What's your email address?",
        4: "What's your ZIP code?",
        5: "How did you hear about us? (Reply: Reddit, Facebook, Google, Friend, Ad, or skip)"
    }
    return prompts.get(step, "Let's continue your setup!")

def format_reminders_list(reminders, user_tz):
    """Format reminders list for display"""
    from datetime import datetime, timedelta
    import pytz

    if not reminders:
        return "You don't have any reminders set."

    tz = pytz.timezone(user_tz)
    user_now = datetime.now(tz)

    scheduled = []
    completed = []

    for reminder_text, reminder_date_utc, sent in reminders:
        try:
            # Handle both datetime objects and strings
            if isinstance(reminder_date_utc, datetime):
                utc_dt = reminder_date_utc
                if utc_dt.tzinfo is None:
                    utc_dt = pytz.UTC.localize(utc_dt)
            else:
                utc_dt = datetime.strptime(str(reminder_date_utc), '%Y-%m-%d %H:%M:%S')
                utc_dt = pytz.UTC.localize(utc_dt)
            user_dt = utc_dt.astimezone(tz)

            # Smart date formatting
            if user_dt.date() == user_now.date():
                date_str = f"Today at {user_dt.strftime('%I:%M %p')}"
            elif user_dt.date() == (user_now + timedelta(days=1)).date():
                date_str = f"Tomorrow at {user_dt.strftime('%I:%M %p')}"
            else:
                date_str = user_dt.strftime('%a, %b %d at %I:%M %p')

            if sent:
                completed.append((reminder_text, date_str))
            else:
                scheduled.append((reminder_text, date_str))
        except:
            if sent:
                completed.append((reminder_text, ""))
            else:
                scheduled.append((reminder_text, ""))

    # Build response
    lines = []

    if scheduled:
        lines.append("SCHEDULED:")
        lines.append("")
        for i, (text, date) in enumerate(scheduled, 1):
            if date:
                lines.append(f"{i}. {text}")
                lines.append(f"   {date}")
            else:
                lines.append(f"{i}. {text}")
            lines.append("")  # Empty line between reminders

    if completed:
        if lines:
            lines.append("")
        lines.append("COMPLETED:")
        lines.append("")
        for i, (text, date) in enumerate(completed[-5:], 1):
            if date:
                lines.append(f"{i}. {text}")
                lines.append(f"   {date}")
            else:
                lines.append(f"{i}. {text}")
            lines.append("")  # Empty line between reminders

    return "\n".join(lines).strip() if lines else "You don't have any reminders set."
