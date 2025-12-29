"""
SMS Reminders - Celery Worker Entrypoint
This file provides a convenient entry point for starting Celery workers.

Usage:
    celery -A worker worker --loglevel=info
    celery -A worker beat --loglevel=info

Or using celery_app directly:
    celery -A celery_app worker --loglevel=info
    celery -A celery_app beat --loglevel=info
"""

from celery_app import celery_app
from database import init_db
from config import logger

# Re-export celery_app for Celery CLI
app = celery_app

# Initialize database on worker startup
@celery_app.on_after_configure.connect
def setup_db(sender, **kwargs):
    """Initialize database when Celery worker starts"""
    logger.info("Celery worker starting - initializing database...")
    init_db()
    logger.info("Database initialized for Celery worker")

if __name__ == "__main__":
    # Allow running directly for local development
    celery_app.start()
