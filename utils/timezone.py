"""
Timezone Utilities
Helper functions for timezone conversions and formatting
"""

from datetime import datetime
from typing import Optional

import pytz
from models.user import get_user_timezone
from config import logger


def get_timezone_from_zip(zip_code: str) -> str:
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

def get_user_current_time(phone_number: str) -> datetime:
    """Get current time in user's timezone"""
    tz_str = get_user_timezone(phone_number)
    user_tz = pytz.timezone(tz_str)
    return datetime.now(user_tz)


def parse_timezone_input(tz_input: Optional[str]) -> Optional[str]:
    """
    Parse user timezone input and return a valid pytz timezone string.

    Accepts:
    - Standard timezone names: "America/New_York", "US/Pacific"
    - Common abbreviations: "EST", "PST", "CST", "MST"
    - Simple names: "Eastern", "Pacific", "Central", "Mountain"
    - City names: "New York", "Los Angeles", "Chicago"

    Returns:
    - Valid pytz timezone string, or None if unrecognized
    """
    if not tz_input:
        return None

    tz_input_lower = tz_input.lower().strip()

    # Common timezone mappings
    timezone_map = {
        # Simple names
        'eastern': 'America/New_York',
        'east': 'America/New_York',
        'et': 'America/New_York',
        'est': 'America/New_York',
        'edt': 'America/New_York',
        'central': 'America/Chicago',
        'ct': 'America/Chicago',
        'cst': 'America/Chicago',
        'cdt': 'America/Chicago',
        'mountain': 'America/Denver',
        'mt': 'America/Denver',
        'mst': 'America/Denver',
        'mdt': 'America/Denver',
        'pacific': 'America/Los_Angeles',
        'west': 'America/Los_Angeles',
        'pt': 'America/Los_Angeles',
        'pst': 'America/Los_Angeles',
        'pdt': 'America/Los_Angeles',
        'alaska': 'America/Anchorage',
        'akst': 'America/Anchorage',
        'hawaii': 'Pacific/Honolulu',
        'hst': 'Pacific/Honolulu',

        # City names
        'new york': 'America/New_York',
        'newyork': 'America/New_York',
        'nyc': 'America/New_York',
        'boston': 'America/New_York',
        'philadelphia': 'America/New_York',
        'miami': 'America/New_York',
        'atlanta': 'America/New_York',
        'chicago': 'America/Chicago',
        'dallas': 'America/Chicago',
        'houston': 'America/Chicago',
        'denver': 'America/Denver',
        'phoenix': 'America/Phoenix',
        'los angeles': 'America/Los_Angeles',
        'losangeles': 'America/Los_Angeles',
        'la': 'America/Los_Angeles',
        'san francisco': 'America/Los_Angeles',
        'sanfrancisco': 'America/Los_Angeles',
        'seattle': 'America/Los_Angeles',
        'portland': 'America/Los_Angeles',
        'las vegas': 'America/Los_Angeles',
        'lasvegas': 'America/Los_Angeles',
        'san diego': 'America/Los_Angeles',
        'sandiego': 'America/Los_Angeles',
        'anchorage': 'America/Anchorage',
        'honolulu': 'Pacific/Honolulu',

        # State abbreviations (approximate)
        'california': 'America/Los_Angeles',
        'ca': 'America/Los_Angeles',
        'texas': 'America/Chicago',
        'tx': 'America/Chicago',
        'florida': 'America/New_York',
        'fl': 'America/New_York',
        'arizona': 'America/Phoenix',
        'az': 'America/Phoenix',
        'colorado': 'America/Denver',
        'co': 'America/Denver',
    }

    # Check mapping first
    if tz_input_lower in timezone_map:
        return timezone_map[tz_input_lower]

    # Try direct pytz timezone name
    try:
        pytz.timezone(tz_input)
        return tz_input
    except pytz.UnknownTimeZoneError:
        pass

    # Try with "America/" prefix
    try:
        tz_name = f"America/{tz_input.replace(' ', '_').title()}"
        pytz.timezone(tz_name)
        return tz_name
    except pytz.UnknownTimeZoneError:
        pass

    # Try with "US/" prefix
    try:
        tz_name = f"US/{tz_input.title()}"
        pytz.timezone(tz_name)
        return tz_name
    except pytz.UnknownTimeZoneError:
        pass

    return None
