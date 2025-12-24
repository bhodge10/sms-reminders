"""
SMS Service
Handles sending SMS messages via Twilio
"""

from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, logger

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_sms(to_number, message):
    """Send an SMS message via Twilio"""
    try:
        twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number
        )
        logger.info(f"✅ Sent SMS to {to_number}")
    except Exception as e:
        logger.error(f"❌ Error sending SMS to {to_number}: {e}")
