"""
Onboarding Service
Handles new user onboarding flow
"""

import re
from datetime import datetime, timedelta
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

from config import logger, FREE_TRIAL_DAYS, TIER_PREMIUM, APP_BASE_URL
from models.user import get_user, get_onboarding_step, create_or_update_user
from utils.timezone import get_timezone_from_zip, get_user_current_time
from utils.formatting import get_onboarding_prompt
from services.sms_service import send_sms


def validate_email(email):
    """Validate email format and return (is_valid, error_type)"""
    if ' ' in email:
        return False, "spaces"
    if '@' not in email:
        return False, "no_at"
    parts = email.split('@')
    if len(parts) != 2 or '.' not in parts[1]:
        return False, "no_domain"
    return True, None


def get_email_error_message(error_type):
    """Return appropriate error message for email validation failure"""
    messages = {
        "spaces": """Email addresses can't have spaces in them!

What's your email address?
(Should look like: name@email.com)""",
        "no_at": """Oops! That email is missing the @ symbol.

It should look like: yourname@gmail.com

What's your email address?""",
        "no_domain": """Almost! But that email needs a domain (like @gmail.com or @yahoo.com).

What's your email address?"""
    }
    return messages.get(error_type, "Please enter a valid email address:")


def validate_zip_code(zip_input):
    """Validate ZIP code and return (cleaned_zip, error_type)"""
    zip_code = zip_input.strip()

    # Handle ZIP+4 format (12345-6789) - extract first 5 digits
    if '-' in zip_code:
        zip_code = zip_code.split('-')[0]

    # Check for letters (likely a city name)
    if any(c.isalpha() for c in zip_code):
        return None, "city_name"

    # Remove any non-digit characters
    zip_code = ''.join(c for c in zip_code if c.isdigit())

    # Check length
    if len(zip_code) != 5:
        return None, "wrong_length"

    return zip_code, None


def get_zip_error_message(error_type, original_input):
    """Return appropriate error message for ZIP validation failure"""
    if error_type == "city_name":
        return """Hmm, that looks like a city name or address!

I just need the 5-digit ZIP code (like 45202).

What's your ZIP code?"""
    elif error_type == "wrong_length":
        digit_count = len(''.join(c for c in original_input if c.isdigit()))
        if digit_count > 0:
            return f"""ZIP codes are exactly 5 digits!

You entered {digit_count} digit{'s' if digit_count != 1 else ''}. Try again?

What's your 5-digit ZIP code?"""
        else:
            return """Please enter a valid 5-digit ZIP code (like 45202):"""
    return """Please enter a valid 5-digit ZIP code:"""


def handle_onboarding(phone_number, message):
    """Handle onboarding flow for new users"""
    try:
        step = get_onboarding_step(phone_number)
        resp = MessagingResponse()

        message_lower = message.lower().strip()
        message_stripped = message.strip()

        # Expanded service keywords
        service_keywords = ['remind', 'list', 'delete', 'what', 'when', 'where', 'how', 'my',
                           'add', 'show', 'create', 'set', 'save', 'remember']

        # Handle help request during onboarding
        if message_lower in ['help', '?'] and step > 0:
            resp.message(f"""I'm helping you set up your account! It's quick - just 5 questions total.

You're currently on step {step} of 5:
{get_onboarding_prompt(step)}

Why I need this info:
• Name: Personalize your experience
• Email: Account recovery & important updates only
• ZIP: Set your timezone for accurate reminders
• Daily Summary: Optional morning reminder recap

Text "cancel" to cancel setup, or just answer the question to continue!""")
            return Response(content=str(resp), media_type="application/xml")

        # Handle cancel request during onboarding
        if message_lower in ['cancel', 'nevermind', 'quit'] and step > 0:
            create_or_update_user(phone_number, onboarding_step=0)
            resp.message("""No problem! Setup cancelled.

If you change your mind, just text me again and we'll start fresh.

Have a great day! 👋""")
            return Response(content=str(resp), media_type="application/xml")

        # Handle skip requests during email/ZIP steps
        if message_lower in ['skip', 'pass', "i don't want to", "dont want to"]:
            if step == 3:
                resp.message("""I understand privacy concerns! But I need your email for account recovery - if you forget your info or get a new phone, this is how you get back in.

I promise we only use it for:
✅ Account recovery
✅ Critical service updates (like scheduled maintenance)
❌ No marketing emails
❌ No selling your data

What's your email address?""")
                return Response(content=str(resp), media_type="application/xml")
            elif step == 4:
                resp.message("""I totally get it! But here's why I need it:

Without your ZIP code, I can't figure out your timezone. That means reminders might arrive at the wrong time (imagine getting a 2pm reminder at 5am 😬).

Your 5-digit ZIP code helps me send reminders when YOU need them.

What's your ZIP code?""")
                return Response(content=str(resp), media_type="application/xml")

        # Check if user is trying to use the service before completing onboarding
        if any(keyword in message_lower for keyword in service_keywords) and step > 0:
            remaining = 5 - step + 1
            question_word = "question" if remaining == 1 else "questions"
            resp.message(f"""⚠️ Almost there! Please finish setup first.

You're on step {step} of 5 - just {remaining} more {question_word}!

{get_onboarding_prompt(step)}""")
            return Response(content=str(resp), media_type="application/xml")

        if step == 0:
            # Welcome message - ask for first name
            create_or_update_user(phone_number, onboarding_step=1)

            # Check if user texted START specifically
            if message_lower == 'start':
                resp.message("""Welcome to Remyndrs! 👋

Thanks for texting START!

I help you remember anything - from grocery lists to important reminders.

Just 5 quick questions to get started, then you're all set!

What's your first name?""")
            else:
                resp.message("""Welcome to Remyndrs! 👋

I help you remember anything - from grocery lists to important reminders.

Just 5 quick questions to get started, then you're all set!

What's your first name?""")

        elif step == 1:
            # Check for full name (two words)
            words = message_stripped.split()
            if len(words) == 2 and all(word.isalpha() for word in words):
                # User provided full name - skip to email
                first_name, last_name = words[0].title(), words[1].title()
                create_or_update_user(phone_number, first_name=first_name, last_name=last_name, onboarding_step=3)
                resp.message(f"""Nice to meet you, {first_name} {last_name}!

Email for account recovery?

(We only use this for important updates - no spam!)""")
            else:
                # Store first name, ask for last name
                first_name = message_stripped.title()
                create_or_update_user(phone_number, first_name=first_name, onboarding_step=2)
                resp.message(f"Nice to meet you, {first_name}! Last name?")

        elif step == 2:
            # Store last name, ask for email
            last_name = message_stripped.title()
            create_or_update_user(phone_number, last_name=last_name, onboarding_step=3)
            resp.message("""Got it! Email for account recovery?

(We only use this for important updates - no spam!)""")

        elif step == 3:
            # Validate and store email, ask for zip code
            email = message_stripped
            is_valid, error_type = validate_email(email)

            if not is_valid:
                resp.message(get_email_error_message(error_type))
                return Response(content=str(resp), media_type="application/xml")

            create_or_update_user(phone_number, email=email, onboarding_step=4)
            resp.message("""Perfect! ZIP code?

(This helps me send reminders at the right time in your timezone)""")

        elif step == 4:
            # Validate and store zip code, calculate timezone, ask about daily summary
            zip_code, error_type = validate_zip_code(message_stripped)

            if error_type:
                resp.message(get_zip_error_message(error_type, message_stripped))
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

            # Send welcome message with pricing transparency and first action prompt
            welcome_msg = f"""You're all set, {first_name}! 🎉"""
            if summary_msg:
                welcome_msg += f"\n\n{summary_msg}"

            welcome_msg += f"""

You have a FREE {FREE_TRIAL_DAYS}-day Premium trial starting now!

After {FREE_TRIAL_DAYS} days, you choose:
• Premium: $4.99/mo (early adopter rate - save $12!)
• Free tier: 2 reminders/day, still useful
• Cancel anytime: no charge, no hassle

💡 Quick tip: Save this number to your contacts!
(I'll send you a contact card you can tap to save in a moment)

Now let's set your first reminder!

What's something you need to remember?

Try: "Remind me to call mom tomorrow at 2pm"
Or: "Add milk and eggs to my grocery list\""""

            resp.message(welcome_msg)

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
