"""
SMS Reminders - Background Worker
Standalone worker process for checking and sending due reminders
"""

import time
from datetime import datetime

from config import logger, REMINDER_CHECK_INTERVAL
from database import init_db
from models.reminder import get_due_reminders, mark_reminder_sent
from services.sms_service import send_sms

def check_reminders():
    """Check for due reminders and send SMS notifications"""
    logger.info(f"Checking for due reminders at {datetime.utcnow()}")

    try:
        due_reminders = get_due_reminders()

        if due_reminders:
            logger.info(f"Found {len(due_reminders)} due reminders")

            for reminder_id, phone_number, reminder_text in due_reminders:
                try:
                    send_sms(phone_number, f"Reminder: {reminder_text}")
                    mark_reminder_sent(reminder_id)
                    logger.info(f"Sent reminder {reminder_id} to {phone_number}")
                except Exception as e:
                    logger.error(f"Failed to send reminder {reminder_id}: {e}")
        else:
            logger.info("No due reminders")

    except Exception as e:
        logger.error(f"Error checking reminders: {e}")

def main():
    """Main worker loop"""
    logger.info("SMS Reminders Worker starting...")

    # Initialize database connection
    init_db()
    logger.info("Database initialized")

    logger.info(f"Worker running - checking every {REMINDER_CHECK_INTERVAL} seconds")

    while True:
        check_reminders()
        time.sleep(REMINDER_CHECK_INTERVAL)

if __name__ == "__main__":
    main()
