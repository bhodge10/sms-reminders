"""
Celery Tasks for SMS Reminder Processing
Implements atomic reminder claiming with SELECT FOR UPDATE SKIP LOCKED.
"""

from celery import shared_task
from celery.utils.log import get_task_logger

from celery_app import celery_app
from models.reminder import (
    claim_due_reminders,
    mark_reminder_sent,
    update_last_sent_reminder,
    release_stale_claims,
)
from services.sms_service import send_sms
from services.metrics_service import track_reminder_delivery

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def check_and_send_reminders(self):
    """
    Periodic task to check for due reminders and dispatch them.
    Uses SELECT FOR UPDATE SKIP LOCKED for atomic claiming.

    This task runs every 30 seconds via Celery Beat.
    Each invocation claims a batch of reminders atomically.
    """
    try:
        # Claim up to 10 reminders atomically
        reminders = claim_due_reminders(batch_size=10)

        if not reminders:
            logger.debug("No due reminders found")
            return {"processed": 0}

        logger.info(f"Claimed {len(reminders)} reminders for processing")

        # Dispatch individual send tasks for each reminder
        for reminder in reminders:
            try:
                logger.info(f"Dispatching reminder {reminder['id']} for {reminder['phone_number'][-4:]}: {reminder['reminder_text'][:30]}")
                result = send_single_reminder.delay(
                    reminder_id=reminder["id"],
                    phone_number=reminder["phone_number"],
                    reminder_text=reminder["reminder_text"],
                )
                logger.info(f"[DISPATCH SUCCESS] reminder {reminder['id']} queued with task_id={result.id}")
            except Exception as dispatch_err:
                logger.exception(f"[DISPATCH FAILED] reminder {reminder['id']}: {dispatch_err}")

        return {"processed": len(reminders)}

    except Exception as exc:
        logger.exception("Error in check_and_send_reminders")
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    retry_backoff=True,
    retry_backoff_max=300,
)
def send_single_reminder(self, reminder_id: int, phone_number: str, reminder_text: str):
    """
    Send a single SMS reminder via Twilio.
    Marks reminder as sent only after successful delivery.

    Uses exponential backoff for retries (30s, 60s, 120s, max 300s).
    IMPORTANT: Once SMS is sent, we do NOT retry even if subsequent operations fail.

    CRITICAL: We hold the FOR UPDATE lock throughout the entire send+mark operation
    to prevent race conditions where mark_reminder_sent fails and the reminder
    gets picked up again.
    """
    # Log immediately at task start - before ANY other operations
    # Use defensive logging in case phone_number is None
    phone_suffix = phone_number[-4:] if phone_number else "NONE"
    logger.info(f"[TASK START] send_single_reminder received: reminder_id={reminder_id}, phone={phone_suffix}")

    # Validate inputs early
    if not phone_number:
        logger.error(f"[INVALID INPUT] reminder_id={reminder_id} has no phone_number!")
        return {"reminder_id": reminder_id, "status": "error", "reason": "no_phone"}

    from database import get_db_connection, return_db_connection

    conn = None
    try:
        conn = get_db_connection()
        logger.info(f"[DB] Got connection for reminder {reminder_id}")
    except Exception as e:
        logger.error(f"[DB ERROR] Failed to get connection for reminder {reminder_id}: {e}")
        raise self.retry(exc=e)
    try:
        c = conn.cursor()

        # Lock the row for the entire operation - prevents race conditions
        c.execute('SELECT sent FROM reminders WHERE id = %s FOR UPDATE', (reminder_id,))
        result = c.fetchone()

        if result and result[0]:
            logger.warning(f"Reminder {reminder_id} already sent (sent={result[0]}), skipping duplicate")
            conn.commit()
            return {
                "reminder_id": reminder_id,
                "status": "already_sent",
            }

        logger.info(f"Reminder {reminder_id} not yet sent, proceeding to send")

        # Try to send SMS - if this fails, we CAN retry (rollback releases lock)
        try:
            logger.info(f"Sending reminder {reminder_id} to {phone_number}")

            # Format message with snooze option
            message = f"Reminder: {reminder_text}\n\n(Reply SNOOZE to snooze)"

            # Send SMS via Twilio
            send_sms(phone_number, message)

        except Exception as exc:
            # SMS failed - rollback to release lock, then retry
            conn.rollback()
            logger.exception(f"Error sending SMS for reminder {reminder_id}")
            track_reminder_delivery(reminder_id, "failed", str(exc))
            raise self.retry(exc=exc)

        # SMS sent successfully - mark as sent
        # Release the FOR UPDATE lock first, then use a fresh connection to update
        # This avoids any connection state issues with the long-held transaction
        try:
            conn.commit()  # Release the FOR UPDATE lock
            logger.info(f"Released lock for reminder {reminder_id}, now marking as sent")
        except Exception as e:
            logger.error(f"Failed to release lock for reminder {reminder_id}: {e}")

        # Use a completely fresh connection to mark as sent
        # This ensures no transaction state issues
        from database import get_db_connection as get_fresh_conn, return_db_connection as return_fresh_conn
        mark_conn = None
        try:
            mark_conn = get_fresh_conn()
            mark_cursor = mark_conn.cursor()
            mark_cursor.execute('UPDATE reminders SET sent = TRUE WHERE id = %s', (reminder_id,))
            mark_conn.commit()

            # Verify the update actually persisted
            mark_cursor.execute('SELECT sent FROM reminders WHERE id = %s', (reminder_id,))
            verify_result = mark_cursor.fetchone()
            if verify_result and verify_result[0]:
                logger.info(f"[VERIFIED] Reminder {reminder_id} marked as sent (sent={verify_result[0]})")
            else:
                logger.error(f"[VERIFY FAILED] Reminder {reminder_id} sent flag is still {verify_result}")
                # Try one more time with explicit transaction
                mark_cursor.execute('BEGIN')
                mark_cursor.execute('UPDATE reminders SET sent = TRUE WHERE id = %s', (reminder_id,))
                mark_cursor.execute('COMMIT')
                logger.info(f"Retried with explicit BEGIN/COMMIT for reminder {reminder_id}")
        except Exception as e:
            logger.exception(f"Failed to mark reminder {reminder_id} as sent: {e}")
        finally:
            if mark_conn:
                return_fresh_conn(mark_conn)

    except Exception as outer_exc:
        # Catch-all for any unexpected errors
        logger.exception(f"[UNEXPECTED ERROR] in send_single_reminder for {reminder_id}: {outer_exc}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise self.retry(exc=outer_exc)
    finally:
        if conn:
            return_db_connection(conn)

    # These are nice-to-have, don't retry if they fail
    try:
        update_last_sent_reminder(phone_number, reminder_id)
        logger.info(f"Updated last_sent_reminder for {phone_number[-4:]} to reminder {reminder_id}")
    except Exception as e:
        logger.error(f"Failed to update last_sent_reminder: {e}")

    try:
        track_reminder_delivery(reminder_id, "sent")
    except Exception as e:
        logger.error(f"Failed to track delivery metrics: {e}")

    logger.info(f"[TASK COMPLETE] Reminder {reminder_id} sent successfully")
    return {
        "reminder_id": reminder_id,
        "status": "sent",
    }


@celery_app.task
def release_stale_claims_task():
    """
    Release reminders that were claimed but not processed.

    This handles cases where a worker crashes after claiming
    but before sending. Runs every 5 minutes via Beat.
    """
    try:
        count = release_stale_claims(timeout_minutes=5)
        if count > 0:
            logger.warning(f"Released {count} stale reminder claims")
        return {"released": count}
    except Exception as exc:
        logger.exception("Error releasing stale claims")
        raise


@celery_app.task
def analyze_conversations_task():
    """
    Analyze recent conversations for quality issues.
    Runs every 4 hours via Beat.
    """
    try:
        from services.conversation_analyzer import analyze_recent_conversations
        result = analyze_recent_conversations(batch_size=50)
        logger.info(f"Conversation analysis complete: {result}")
        return result
    except Exception as exc:
        logger.exception("Error in conversation analysis task")
        raise
