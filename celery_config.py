"""
Celery Beat Schedule Configuration
Defines periodic tasks for reminder checking.
"""

from datetime import timedelta

# Beat schedule - periodic tasks
beat_schedule = {
    # Check for due reminders every 30 seconds
    "check-reminders-every-30-seconds": {
        "task": "tasks.reminder_tasks.check_and_send_reminders",
        "schedule": timedelta(seconds=30),
        "options": {
            "expires": 25,  # Task expires if not picked up in 25 seconds
        },
    },
    # Release stale claims every 5 minutes (handles crashed workers)
    "release-stale-claims": {
        "task": "tasks.reminder_tasks.release_stale_claims_task",
        "schedule": timedelta(minutes=5),
    },
}

# Task routing (for future scaling with multiple queues)
task_routes = {
    "tasks.reminder_tasks.send_single_reminder": {"queue": "sms"},
    "tasks.reminder_tasks.check_and_send_reminders": {"queue": "celery"},
    "tasks.reminder_tasks.release_stale_claims_task": {"queue": "celery"},
}
