"""
First Action Service
Handles daily summary tip after user's first successful action
"""

from config import logger
from models.user import get_user, create_or_update_user


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
    """Generate a one-shot daily summary tip to append after first reminder"""
    return f"""{action_confirmation}

Tip: Want a daily summary of your reminders each morning? Text SUMMARY ON to enable it!"""


# SMART NUDGES: One-shot tip after first action
# Uncomment post-launch when ready to activate alongside trial auto-enable:
# def get_smart_nudge_prompt_message(action_confirmation):
#     """Generate a one-shot smart nudge tip to append after first action"""
#     return f"""{action_confirmation}
#
# Tip: Want daily AI-powered insights based on your data? Text NUDGE ON to enable!"""
