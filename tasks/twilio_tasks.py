"""
Twilio Cost Polling Tasks
Polls Twilio Usage Records API daily and stores actual SMS costs.
"""

import os
from datetime import date, timedelta

from celery_app import celery_app
from config import logger
from database import get_db_connection, return_db_connection


@celery_app.task(name="tasks.twilio_tasks.poll_twilio_costs")
def poll_twilio_costs():
    """Poll Twilio Usage Records API for yesterday's actual SMS costs.

    Fetches inbound and outbound SMS usage from Twilio's daily usage records,
    then upserts the results into the twilio_costs table. Safe to re-run —
    uses ON CONFLICT to update existing rows.
    """
    # Skip in test environment
    environment = os.environ.get("ENVIRONMENT", "production").lower()
    if environment in ("test", "testing"):
        logger.info("poll_twilio_costs: Skipping in test environment")
        return

    try:
        # Import here to avoid circular imports and to get the initialized client
        from services.sms_service import twilio_client

        if twilio_client is None:
            logger.warning("poll_twilio_costs: Twilio client not initialized, skipping")
            return

        yesterday = date.today() - timedelta(days=1)

        # Fetch inbound SMS usage
        inbound_records = twilio_client.usage.records.daily.list(
            category="sms-inbound",
            start_date=yesterday,
            end_date=yesterday,
        )
        inbound_count = 0
        inbound_cost = 0.0
        for record in inbound_records:
            inbound_count += int(record.count)
            inbound_cost += float(record.price) if record.price else 0.0

        # Fetch outbound SMS usage
        outbound_records = twilio_client.usage.records.daily.list(
            category="sms-outbound",
            start_date=yesterday,
            end_date=yesterday,
        )
        outbound_count = 0
        outbound_cost = 0.0
        for record in outbound_records:
            outbound_count += int(record.count)
            outbound_cost += float(record.price) if record.price else 0.0

        # Twilio reports costs as negative values — use absolute values
        inbound_cost = abs(inbound_cost)
        outbound_cost = abs(outbound_cost)
        total_cost = inbound_cost + outbound_cost

        # Upsert into twilio_costs table
        conn = None
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO twilio_costs (cost_date, inbound_count, inbound_cost, outbound_count, outbound_cost, total_cost)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (cost_date) DO UPDATE SET
                    inbound_count = EXCLUDED.inbound_count,
                    inbound_cost = EXCLUDED.inbound_cost,
                    outbound_count = EXCLUDED.outbound_count,
                    outbound_cost = EXCLUDED.outbound_cost,
                    total_cost = EXCLUDED.total_cost
            ''', (yesterday, inbound_count, inbound_cost, outbound_count, outbound_cost, total_cost))
            conn.commit()

            logger.info(
                f"poll_twilio_costs: {yesterday} — "
                f"inbound: {inbound_count} msgs / ${inbound_cost:.4f}, "
                f"outbound: {outbound_count} msgs / ${outbound_cost:.4f}, "
                f"total: ${total_cost:.4f}"
            )
        finally:
            if conn:
                return_db_connection(conn)

    except Exception as e:
        logger.error(f"poll_twilio_costs: Error polling Twilio usage — {e}")
        raise
