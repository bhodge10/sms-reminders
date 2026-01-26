"""
Database Helper Utilities
Provides common patterns for database operations with encryption support
"""

from typing import Optional, Tuple, Any, List
from config import ENCRYPTION_ENABLED, logger


def get_phone_lookup_params(phone_number: str) -> Tuple[Optional[str], str]:
    """
    Get phone hash and phone number for database lookups.

    Returns:
        Tuple of (phone_hash or None, phone_number)
    """
    if ENCRYPTION_ENABLED:
        from utils.encryption import hash_phone
        return (hash_phone(phone_number), phone_number)
    return (None, phone_number)


def execute_with_phone_lookup(
    cursor: Any,
    query_template: str,
    phone_number: str,
    extra_params: Tuple = ()
) -> Optional[Any]:
    """
    Execute a SELECT query with encryption-aware phone lookup.
    Tries phone_hash first (if enabled), falls back to phone_number.

    Args:
        cursor: Database cursor
        query_template: SQL query with {phone_condition} placeholder
                       Example: "SELECT * FROM users WHERE {phone_condition}"
        phone_number: User's phone number
        extra_params: Additional parameters to append after phone lookup param

    Returns:
        First row result or None
    """
    if ENCRYPTION_ENABLED:
        from utils.encryption import hash_phone
        phone_hash = hash_phone(phone_number)

        # Try phone_hash first
        query = query_template.format(phone_condition="phone_hash = %s")
        cursor.execute(query, (phone_hash,) + extra_params)
        result = cursor.fetchone()

        if not result:
            # Fallback for users created before encryption
            query = query_template.format(phone_condition="phone_number = %s")
            cursor.execute(query, (phone_number,) + extra_params)
            result = cursor.fetchone()
    else:
        query = query_template.format(phone_condition="phone_number = %s")
        cursor.execute(query, (phone_number,) + extra_params)
        result = cursor.fetchone()

    return result


def execute_update_with_phone_lookup(
    cursor: Any,
    query_template: str,
    phone_number: str,
    params: Tuple = ()
) -> int:
    """
    Execute an UPDATE query with encryption-aware phone lookup.
    Tries phone_hash first (if enabled), falls back to phone_number if no rows affected.

    Args:
        cursor: Database cursor
        query_template: SQL query with {phone_condition} placeholder
                       Example: "UPDATE users SET field = %s WHERE {phone_condition}"
        phone_number: User's phone number
        params: Parameters for the query (before the phone lookup param)

    Returns:
        Number of rows affected
    """
    if ENCRYPTION_ENABLED:
        from utils.encryption import hash_phone
        phone_hash = hash_phone(phone_number)

        # Try phone_hash first
        query = query_template.format(phone_condition="phone_hash = %s")
        cursor.execute(query, params + (phone_hash,))

        if cursor.rowcount == 0:
            # Fallback for users created before encryption
            query = query_template.format(phone_condition="phone_number = %s")
            cursor.execute(query, params + (phone_number,))
    else:
        query = query_template.format(phone_condition="phone_number = %s")
        cursor.execute(query, params + (phone_number,))

    return cursor.rowcount


# Standard column list for users table (maintains backward compatibility with index-based access)
USER_COLUMNS = """
    phone_number, first_name, last_name, email, zip_code, timezone,
    onboarding_complete, onboarding_step, created_at, pending_delete,
    pending_reminder_text, pending_reminder_time, referral_source,
    premium_status, premium_since, last_active_at, signup_source, total_messages,
    five_minute_nudge_scheduled_at, five_minute_nudge_sent, post_onboarding_interactions
""".strip()

# Column indices for users table (for self-documenting code)
class UserColumn:
    """Column indices for users table SELECT queries using USER_COLUMNS."""
    PHONE_NUMBER = 0
    FIRST_NAME = 1
    LAST_NAME = 2
    EMAIL = 3
    ZIP_CODE = 4
    TIMEZONE = 5
    ONBOARDING_COMPLETE = 6
    ONBOARDING_STEP = 7
    CREATED_AT = 8
    PENDING_DELETE = 9
    PENDING_REMINDER_TEXT = 10
    PENDING_REMINDER_TIME = 11
    REFERRAL_SOURCE = 12
    PREMIUM_STATUS = 13
    PREMIUM_SINCE = 14
    LAST_ACTIVE_AT = 15
    SIGNUP_SOURCE = 16
    TOTAL_MESSAGES = 17
    FIVE_MINUTE_NUDGE_SCHEDULED_AT = 18
    FIVE_MINUTE_NUDGE_SENT = 19
    POST_ONBOARDING_INTERACTIONS = 20
