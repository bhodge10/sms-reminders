"""
Onboarding Service
Handles new user onboarding flow
"""

from datetime import datetime, timedelta
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

from config import logger, FREE_TRIAL_DAYS, TIER_PREMIUM, APP_BASE_URL
from models.user import get_user, get_onboarding_step, create_or_update_user
from utils.timezone import get_timezone_from_zip, get_user_current_time
from utils.formatting import get_onboarding_prompt
from services.sms_service import send_sms

def handle_onboarding(phone_number, message):
    """Handle onboarding flow for new users"""
    try:
        step = get_onboarding_step(phone_number)
        resp = MessagingResponse()

        message_lower = message.lower().strip()
        service_keywords = ['remind', 'list', 'delete', 'what', 'when', 'where', 'how', 'my']

        # Check if user is trying to use the service before completing onboarding
        if any(keyword in message_lower for keyword in service_keywords) and step > 0:
            resp.message(f"""⚠️ Please complete your setup first!

You're on step {step} of 5. Let's finish quickly:

{get_onboarding_prompt(step)}""")
            return Response(content=str(resp), media_type="application/xml")

        if step == 0:
            # Welcome message - ask for first name
            create_or_update_user(phone_number, onboarding_step=1)
            resp.message("""Welcome to Remyndrs! 👋

I help you remember details about your stuff and set reminders.

Just 5 quick questions to get started, then you're all set!

Note: During beta, you may experience brief periods without replies or delayed reminders as we roll out updates.

Tip: Text ? anytime for help.

What's your first name?""")

        elif step == 1:
            # Store first name, ask for last name
            first_name = message.strip()
            create_or_update_user(phone_number, first_name=first_name, onboarding_step=2)
            resp.message(f"Nice to meet you, {first_name}! Last name?")

        elif step == 2:
            # Store last name, ask for email
            last_name = message.strip()
            create_or_update_user(phone_number, last_name=last_name, onboarding_step=3)
            resp.message("Got it! Email address?")

        elif step == 3:
            # Store email, ask for zip code
            email = message.strip()
            create_or_update_user(phone_number, email=email, onboarding_step=4)
            resp.message("Almost done! ZIP code? (for your timezone)")

        elif step == 4:
            # Store zip code, calculate timezone, ask about daily summary
            zip_code = message.strip()

            # Validate zip code (basic validation)
            if not zip_code.isdigit() or len(zip_code) != 5:
                resp.message("Please enter a valid 5-digit ZIP code:")
                return Response(content=str(resp), media_type="application/xml")

            # Get timezone from zip code
            timezone = get_timezone_from_zip(zip_code)

            # Save zip and timezone, move to step 5
            create_or_update_user(
                phone_number,
                zip_code=zip_code,
                timezone=timezone,
                onboarding_step=5
            )

            resp.message(f"""Got it! Your timezone is set to {timezone}.

Last question: Would you like a daily summary of your reminders each morning?

Reply YES for 8am summary, or a time like 7AM or 9:30AM.
Reply NO to skip.""")

        elif step == 5:
            # Handle daily summary preference, complete onboarding
            import re
            msg_lower = message.lower().strip()

            # Calculate trial end date
            trial_end_date = datetime.utcnow() + timedelta(days=FREE_TRIAL_DAYS)

            summary_msg = ""

            if msg_lower in ['yes', 'y', 'sure', 'ok', 'okay', 'yep', 'yeah']:
                # Enable with default 8am
                create_or_update_user(
                    phone_number,
                    daily_summary_enabled=True,
                    daily_summary_time='08:00',
                    onboarding_complete=True,
                    onboarding_step=6,
                    premium_status=TIER_PREMIUM,
                    trial_end_date=trial_end_date
                )
                summary_msg = "Daily summary enabled for 8:00 AM!"
            elif msg_lower in ['no', 'n', 'skip', 'nope', 'nah']:
                create_or_update_user(
                    phone_number,
                    onboarding_complete=True,
                    onboarding_step=6,
                    premium_status=TIER_PREMIUM,
                    trial_end_date=trial_end_date
                )
            else:
                # Try to parse a time
                time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', msg_lower, re.IGNORECASE)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2)) if time_match.group(2) else 0
                    am_pm = time_match.group(3).upper()

                    if am_pm == 'PM' and hour != 12:
                        hour += 12
                    elif am_pm == 'AM' and hour == 12:
                        hour = 0

                    time_str = f"{hour:02d}:{minute:02d}"

                    # Format display time
                    display_am_pm = 'AM' if hour < 12 else 'PM'
                    display_hour = hour if hour <= 12 else hour - 12
                    if display_hour == 0:
                        display_hour = 12
                    display_time = f"{display_hour}:{minute:02d} {display_am_pm}"

                    create_or_update_user(
                        phone_number,
                        daily_summary_enabled=True,
                        daily_summary_time=time_str,
                        onboarding_complete=True,
                        onboarding_step=6,
                        premium_status=TIER_PREMIUM,
                        trial_end_date=trial_end_date
                    )
                    summary_msg = f"Daily summary enabled for {display_time}!"
                else:
                    # Unclear response, skip and complete
                    create_or_update_user(
                        phone_number,
                        onboarding_complete=True,
                        onboarding_step=6,
                        premium_status=TIER_PREMIUM,
                        trial_end_date=trial_end_date
                    )

            # Get user info for personalized message
            user = get_user(phone_number)
            first_name = user[1]
            timezone = user[5] or 'America/New_York'
            user_time = get_user_current_time(phone_number)

            # Build welcome message
            welcome_lines = [f"You're all set, {first_name}!"]
            if summary_msg:
                welcome_lines.append(f"\n{summary_msg}")
            welcome_lines.append(f"\n🎉 You have a FREE {FREE_TRIAL_DAYS}-day Premium trial!")
            welcome_lines.append("""
Try these:
📝 "Add milk, eggs, bread to grocery list"
🧠 "Remember I parked on Level 3 spot 1"
⏰ "Remind me to call mom tomorrow at 2pm"
""")
            welcome_lines.append(f"Your timezone: {timezone}")
            welcome_lines.append(f"Your current time: {user_time.strftime('%I:%M %p')}")
            welcome_lines.append("\nText ? anytime for help.")

            resp.message("".join(welcome_lines))

            # Send VCF contact card as separate follow-up MMS
            vcf_url = f"{APP_BASE_URL}/contact.vcf"
            send_sms(
                phone_number,
                "📱 Tap to save Remyndrs to your contacts!",
                media_url=vcf_url
            )

        return Response(content=str(resp), media_type="application/xml")
    
    except Exception as e:
        logger.error(f"❌ Error in onboarding for {phone_number}: {e}")
        resp = MessagingResponse()
        resp.message("Sorry, something went wrong. Please try again.")
        return Response(content=str(resp), media_type="application/xml")
