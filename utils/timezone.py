"""
Timezone Utilities
Helper functions for timezone conversions and formatting
"""

from datetime import datetime
import pytz
from models.user import get_user_timezone
from config import logger

def get_timezone_from_zip(zip_code):
    """Convert zip code to timezone using first digit mapping"""
    try:
        first_digit = zip_code[0]

        # ZIP code first digit to timezone mapping
        # 0-3 = Eastern, 5-6-7 = Central, 8 = Mountain, 9 = Pacific
        if first_digit in ['0', '1', '2', '3']:
            return 'America/New_York'  # Eastern
        elif first_digit in ['5', '6', '7']:
            return 'America/Chicago'  # Central
        elif first_digit == '8':
            return 'America/Denver'  # Mountain
        elif first_digit == '9':
            return 'America/Los_Angeles'  # Pacific
        else:
            return 'America/New_York'  # Default to Eastern
    except Exception as e:
        logger.error(f"Error getting timezone from zip: {e}")
        return 'America/New_York'

def get_user_current_time(phone_number):
    """Get current time in user's timezone"""
    tz_str = get_user_timezone(phone_number)
    user_tz = pytz.timezone(tz_str)
    return datetime.now(user_tz)
