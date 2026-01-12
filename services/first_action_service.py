"""
First Action Service
Handles daily summary prompt after user's first successful action
"""

import re
from config import logger
from models.user import get_user, create_or_update_user
from utils.timezone import get_user_current_time


def should_prompt_daily_summary(phone_number):
    """Check if we should prompt user for daily summary after their action"""
    user = get_user(phone_number)
    if not user:
        return False

    # Check if daily_summary_prompted column exists and is set
    # User tuple indices may vary - need to check by field name approach
    # For now, check if daily_summary_enabled is None/False and not yet prompted
    try:
        # Get user's daily_summary_enabled status
        # If they already have it enabled or have been prompted, don't ask again
        daily_summary_enabled = get_daily_summary_status(phone_number)
        daily_summary_prompted = get_daily_summary_prompted(phone_number)

        # Only prompt if:
        # 1. They haven't been prompted yet
        # 2. They don't already have daily summary enabled
        if daily_summary_prompted:
            return False
        if daily_summary_enabled:
            return False

        return True
    except Exception as e:
        logger.error(f"Error checking daily summary prompt status: {e}")
        return False


def get_daily_summary_status(phone_number):
    """Get user's daily summary enabled status"""
    from database import get_db_connection, return_db_connection
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT daily_summary_enabled FROM users WHERE phone_number = %s', (phone_number,))
        result = c.fetchone()
        return result[0] if result else False
    except Exception as e:
        logger.error(f"Error getting daily summary status: {e}")
        return False
    finally:
        if conn:
            return_db_connection(conn)


def get_daily_summary_prompted(phone_number):
    """Check if user has been prompted for daily summary"""
    from database import get_db_connection, return_db_connection
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT daily_summary_prompted FROM users WHERE phone_number = %s', (phone_number,))
        result = c.fetchone()
        return result[0] if result else False
    except Exception as e:
        # Column might not exist yet - return False
        logger.debug(f"daily_summary_prompted column may not exist: {e}")
        return False
    finally:
        if conn:
            return_db_connection(conn)


def mark_daily_summary_prompted(phone_number):
    """Mark that user has been prompted for daily summary"""
    create_or_update_user(phone_number, daily_summary_prompted=True)


def get_daily_summary_prompt_message(action_confirmation):
    """Generate the daily summary prompt message to append after first action"""
    return f"""{action_confirmation}

You're getting the hang of it!

Quick question: Want a daily text each morning with your reminders for the day?

This helps you plan ahead and never miss anything.

Reply:
• YES (I'll send at 8am)
• A time like 7AM or 9:30AM
• NO (you can enable later with "daily summary on")"""


def handle_daily_summary_response(phone_number, message):
    """
    Handle user's response to daily summary prompt.
    Returns (handled, response_text) tuple.
    - handled: True if this was a daily summary response
    - response_text: The response to send (or None if not handled)
    """
    msg_lower = message.lower().strip()

    # Check if user was prompted for daily summary
    if not get_daily_summary_prompted(phone_number):
        return False, None

    # Check if daily summary is already configured
    if get_daily_summary_status(phone_number):
        return False, None

    user = get_user(phone_number)
    if not user:
        return False, None

    first_name = user[1] or "there"
    timezone = user[5] or 'America/New_York'

    # Get current time for display
    try:
        user_time = get_user_current_time(phone_number)
        current_time = user_time.strftime('%I:%M %p')
    except:
        current_time = ""

    response_text = None

    if msg_lower in ['yes', 'y', 'sure', 'ok', 'okay', 'yep', 'yeah']:
        # Enable with default 8am
        create_or_update_user(
            phone_number,
            daily_summary_enabled=True,
            daily_summary_time='08:00'
        )
        response_text = build_welcome_message("8:00 AM", timezone, current_time)

    elif msg_lower in ['no', 'n', 'nope', 'nah', 'skip']:
        # User declined - just mark as complete
        response_text = build_welcome_message(None, timezone, current_time)

    else:
        # Try to parse a time
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', msg_lower, re.IGNORECASE)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            am_pm = time_match.group(3).upper()

            if am_pm == 'PM' and hour != 12:
                hour += 12
            elif am_pm == 'AM' and hour == 12:
                hour = 0

            time_str = f"{hour:02d}:{minute:02d}"

            # Format display time
            display_am_pm = 'AM' if hour < 12 else 'PM'
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            display_time = f"{display_hour}:{minute:02d} {display_am_pm}"

            create_or_update_user(
                phone_number,
                daily_summary_enabled=True,
                daily_summary_time=time_str
            )
            response_text = build_welcome_message(display_time, timezone, current_time)
        else:
            # Not a recognizable response - don't handle
            return False, None

    return True, response_text


def build_welcome_message(summary_time, timezone, current_time):
    """Build the comprehensive welcome message after daily summary choice"""
    if summary_time:
        header = f"Great! You'll get your daily summary at {summary_time} each morning. 📅"
    else:
        header = "No problem! You can always enable it later by texting \"daily summary on\""

    message = f"""{header}

Here's what else I can do:

📝 Lists
"Add milk, eggs to grocery list"
"What's on my grocery list?"
"Clear my grocery list"

🧠 Remember Things
"Remember: garage code is 4582"
"What's my garage code?"
"Save: WiFi password is HomeNet123"

⏰ Reminders
"Show my reminders for this week"
"Remind me every Monday at 9am to take out trash"
"Remind me to call mom in 2 hours"

🔍 Search Your Memories
"What did I save about my car?"
"Show everything about passwords"

Text ? for help or "commands" for the complete list.

---
Your timezone: {timezone}"""

    if current_time:
        message += f"\nYour local time: {current_time}"

    message += """

Beta Note: We're actively improving the service. You may occasionally experience brief delays during updates. Text "support" if you have issues!

Welcome to Remyndrs! 🎉"""

    return message
