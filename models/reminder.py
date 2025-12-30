"""
Reminder Model
Handles all reminder-related database operations
"""

from datetime import datetime
from database import get_db_connection, return_db_connection
from config import logger, ENCRYPTION_ENABLED

def save_reminder(phone_number, reminder_text, reminder_date):
    """Save a new reminder to the database with optional encryption"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        if ENCRYPTION_ENABLED:
            from utils.encryption import encrypt_field, hash_phone
            phone_hash = hash_phone(phone_number)
            reminder_text_encrypted = encrypt_field(reminder_text)
            c.execute(
                '''INSERT INTO reminders (phone_number, phone_hash, reminder_text, reminder_text_encrypted, reminder_date)
                   VALUES (%s, %s, %s, %s, %s)''',
                (phone_number, phone_hash, reminder_text, reminder_text_encrypted, reminder_date)
            )
        else:
            c.execute(
                'INSERT INTO reminders (phone_number, reminder_text, reminder_date) VALUES (%s, %s, %s)',
                (phone_number, reminder_text, reminder_date)
            )

        conn.commit()
        logger.info(f"Saved reminder at {reminder_date}")
    except Exception as e:
        logger.error(f"Error saving reminder: {e}")
    finally:
        if conn:
            return_db_connection(conn)

def get_due_reminders():
    """Get all reminders that are due to be sent"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        c.execute(
            'SELECT id, phone_number, reminder_text FROM reminders WHERE reminder_date <= %s AND sent = FALSE',
            (now,)
        )
        results = c.fetchall()
        return results
    except Exception as e:
        logger.error(f"Error getting due reminders: {e}")
        return []
    finally:
        if conn:
            return_db_connection(conn)

def mark_reminder_sent(reminder_id):
    """Mark a reminder as sent. Raises exception on failure to trigger retry."""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('UPDATE reminders SET sent = TRUE WHERE id = %s', (reminder_id,))
        conn.commit()
        logger.info(f"Marked reminder {reminder_id} as sent")
    except Exception as e:
        logger.error(f"Error marking reminder sent: {e}")
        raise  # Re-raise so Celery task knows to retry
    finally:
        if conn:
            return_db_connection(conn)

def get_user_reminders(phone_number):
    """Get all reminders for a user (both pending and sent)"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        if ENCRYPTION_ENABLED:
            from utils.encryption import hash_phone
            phone_hash = hash_phone(phone_number)
            c.execute(
                'SELECT reminder_text, reminder_date, sent FROM reminders WHERE phone_hash = %s ORDER BY reminder_date',
                (phone_hash,)
            )
            results = c.fetchall()
            if not results:
                # Fallback for reminders created before encryption
                c.execute(
                    'SELECT reminder_text, reminder_date, sent FROM reminders WHERE phone_number = %s ORDER BY reminder_date',
                    (phone_number,)
                )
                results = c.fetchall()
        else:
            c.execute(
                'SELECT reminder_text, reminder_date, sent FROM reminders WHERE phone_number = %s ORDER BY reminder_date',
                (phone_number,)
            )
            results = c.fetchall()

        return results
    except Exception as e:
        logger.error(f"Error getting user reminders: {e}")
        return []
    finally:
        if conn:
            return_db_connection(conn)


def get_pending_reminders(phone_number):
    """Get all pending (not yet sent) reminders for a user with IDs"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        if ENCRYPTION_ENABLED:
            from utils.encryption import hash_phone
            phone_hash = hash_phone(phone_number)
            c.execute(
                'SELECT id, reminder_text, reminder_date FROM reminders WHERE phone_hash = %s AND sent = FALSE ORDER BY reminder_date',
                (phone_hash,)
            )
            results = c.fetchall()
            if not results:
                # Fallback for reminders created before encryption
                c.execute(
                    'SELECT id, reminder_text, reminder_date FROM reminders WHERE phone_number = %s AND sent = FALSE ORDER BY reminder_date',
                    (phone_number,)
                )
                results = c.fetchall()
        else:
            c.execute(
                'SELECT id, reminder_text, reminder_date FROM reminders WHERE phone_number = %s AND sent = FALSE ORDER BY reminder_date',
                (phone_number,)
            )
            results = c.fetchall()

        return results
    except Exception as e:
        logger.error(f"Error getting pending reminders: {e}")
        return []
    finally:
        if conn:
            return_db_connection(conn)


def search_pending_reminders(phone_number, search_term):
    """Search pending reminders by keyword (case-insensitive)"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        search_pattern = f'%{search_term}%'

        if ENCRYPTION_ENABLED:
            from utils.encryption import hash_phone
            phone_hash = hash_phone(phone_number)
            c.execute(
                '''SELECT id, reminder_text, reminder_date FROM reminders
                   WHERE phone_hash = %s AND sent = FALSE AND LOWER(reminder_text) LIKE LOWER(%s)
                   ORDER BY reminder_date''',
                (phone_hash, search_pattern)
            )
            results = c.fetchall()
            if not results:
                # Fallback for reminders created before encryption
                c.execute(
                    '''SELECT id, reminder_text, reminder_date FROM reminders
                       WHERE phone_number = %s AND sent = FALSE AND LOWER(reminder_text) LIKE LOWER(%s)
                       ORDER BY reminder_date''',
                    (phone_number, search_pattern)
                )
                results = c.fetchall()
        else:
            c.execute(
                '''SELECT id, reminder_text, reminder_date FROM reminders
                   WHERE phone_number = %s AND sent = FALSE AND LOWER(reminder_text) LIKE LOWER(%s)
                   ORDER BY reminder_date''',
                (phone_number, search_pattern)
            )
            results = c.fetchall()

        return results
    except Exception as e:
        logger.error(f"Error searching pending reminders: {e}")
        return []
    finally:
        if conn:
            return_db_connection(conn)


def delete_reminder(phone_number, reminder_id):
    """Delete a specific pending reminder by ID (only if not sent)"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        if ENCRYPTION_ENABLED:
            from utils.encryption import hash_phone
            phone_hash = hash_phone(phone_number)
            # Only delete if it belongs to this user and hasn't been sent
            c.execute(
                'DELETE FROM reminders WHERE id = %s AND phone_hash = %s AND sent = FALSE',
                (reminder_id, phone_hash)
            )
            if c.rowcount == 0:
                # Fallback for reminders created before encryption
                c.execute(
                    'DELETE FROM reminders WHERE id = %s AND phone_number = %s AND sent = FALSE',
                    (reminder_id, phone_number)
                )
        else:
            c.execute(
                'DELETE FROM reminders WHERE id = %s AND phone_number = %s AND sent = FALSE',
                (reminder_id, phone_number)
            )

        deleted = c.rowcount > 0
        conn.commit()
        if deleted:
            logger.info(f"Deleted reminder {reminder_id}")
        return deleted
    except Exception as e:
        logger.error(f"Error deleting reminder: {e}")
        return False
    finally:
        if conn:
            return_db_connection(conn)


def update_last_sent_reminder(phone_number, reminder_id):
    """Update the last sent reminder for a user (for snooze detection)"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            'UPDATE users SET last_sent_reminder_id = %s, last_sent_reminder_at = %s WHERE phone_number = %s',
            (reminder_id, datetime.utcnow(), phone_number)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating last sent reminder: {e}")
    finally:
        if conn:
            return_db_connection(conn)


def get_last_sent_reminder(phone_number, max_age_minutes=30):
    """Get the last sent reminder for a user if within the snooze window"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Get the last sent reminder info from users table
        c.execute(
            '''SELECT last_sent_reminder_id, last_sent_reminder_at
               FROM users WHERE phone_number = %s''',
            (phone_number,)
        )
        result = c.fetchone()

        if not result or not result[0] or not result[1]:
            return None

        reminder_id, sent_at = result

        # Check if within the snooze window
        if isinstance(sent_at, datetime):
            age_minutes = (datetime.utcnow() - sent_at).total_seconds() / 60
            if age_minutes > max_age_minutes:
                return None
        else:
            return None

        # Get the reminder details
        c.execute(
            'SELECT id, reminder_text FROM reminders WHERE id = %s',
            (reminder_id,)
        )
        reminder = c.fetchone()

        if reminder:
            return {'id': reminder[0], 'text': reminder[1], 'sent_at': sent_at}
        return None

    except Exception as e:
        logger.error(f"Error getting last sent reminder: {e}")
        return None
    finally:
        if conn:
            return_db_connection(conn)


def mark_reminder_snoozed(reminder_id):
    """Mark a reminder as snoozed"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('UPDATE reminders SET snoozed = TRUE WHERE id = %s', (reminder_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"Error marking reminder snoozed: {e}")
    finally:
        if conn:
            return_db_connection(conn)


def claim_due_reminders(batch_size=10):
    """
    Atomically claim due reminders using SELECT FOR UPDATE SKIP LOCKED.

    This prevents race conditions when multiple workers try to claim
    the same reminder. SKIP LOCKED ensures workers don't block each other.

    Args:
        batch_size: Maximum number of reminders to claim per call

    Returns:
        List of claimed reminder dicts with id, phone_number, reminder_text
    """
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        # Claim reminders atomically with SKIP LOCKED
        # This query:
        # 1. Finds due reminders that haven't been sent and aren't claimed
        # 2. Locks them (other workers will skip these rows)
        # 3. Updates claimed_at to mark them as in-progress
        # 4. Returns the claimed reminders
        c.execute("""
            WITH claimed AS (
                SELECT id, phone_number, reminder_text
                FROM reminders
                WHERE reminder_date <= %s
                  AND sent = FALSE
                  AND (claimed_at IS NULL OR claimed_at < NOW() - INTERVAL '5 minutes')
                ORDER BY reminder_date ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            )
            UPDATE reminders r
            SET claimed_at = NOW()
            FROM claimed c
            WHERE r.id = c.id
            RETURNING r.id, r.phone_number, r.reminder_text
        """, (now, batch_size))

        results = c.fetchall()
        conn.commit()

        # Convert to list of dicts
        return [
            {
                "id": row[0],
                "phone_number": row[1],
                "reminder_text": row[2],
            }
            for row in results
        ]

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error claiming due reminders: {e}")
        return []
    finally:
        if conn:
            return_db_connection(conn)


def release_stale_claims(timeout_minutes=5):
    """
    Release reminders that were claimed but not processed.

    This handles cases where a worker crashes after claiming
    but before sending. Should be run periodically.

    Args:
        timeout_minutes: How old a claim must be to be considered stale

    Returns:
        Number of reminders released
    """
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE reminders
            SET claimed_at = NULL
            WHERE claimed_at IS NOT NULL
              AND sent = FALSE
              AND claimed_at < NOW() - INTERVAL '%s minutes'
        """, (timeout_minutes,))
        count = c.rowcount
        conn.commit()
        if count > 0:
            logger.info(f"Released {count} stale reminder claims")
        return count
    except Exception as e:
        logger.error(f"Error releasing stale claims: {e}")
        return 0
    finally:
        if conn:
            return_db_connection(conn)
