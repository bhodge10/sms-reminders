#!/usr/bin/env python
"""Extended test for the confidence-based confirmation system"""

import requests
import re
import time

API_URL = "http://localhost:8000/sms"
TEST_PHONE = "+15551234999"  # Existing onboarded test user

def parse_twiml_response(xml_text):
    match = re.search(r'<Message>(.*?)</Message>', xml_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return xml_text

def safe_print(text):
    print(text.encode('ascii', 'replace').decode('ascii'))

def send_message(message):
    response = requests.post(
        API_URL,
        data={"Body": message, "From": TEST_PHONE},
        timeout=60
    )
    return parse_twiml_response(response.text)

def test_reminder(description, message, expected_confidence="unknown"):
    """Test a reminder and report the result"""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"Expected confidence: {expected_confidence}")
    print(f"Input: '{message}'")
    print("-"*60)

    response = send_message(message)
    safe_print(f"Response: {response[:300]}")

    if "Is that right?" in response or "Reply YES" in response:
        result = "LOW CONFIDENCE - Asked for confirmation"
        # Say no to avoid creating reminder
        time.sleep(1)
        send_message("no")
    elif "I'll remind you" in response or "Got it!" in response:
        result = "HIGH CONFIDENCE - Created immediately"
    elif "What time" in response or "which day" in response.lower():
        result = "NEEDS CLARIFICATION - Missing info"
    else:
        result = "OTHER RESPONSE"

    print(f"RESULT: {result}")
    time.sleep(1.5)
    return result

print("="*60)
print("CONFIDENCE-BASED CONFIRMATION SYSTEM TEST")
print("="*60)
print(f"Using existing test phone: {TEST_PHONE}")
print("Testing various reminder requests with different ambiguity levels")

# ==========================================
# HIGH CONFIDENCE TESTS (should create immediately)
# ==========================================
print("\n\n" + "="*60)
print("SECTION 1: HIGH CONFIDENCE (should create immediately)")
print("="*60)

test_reminder(
    "Clear time and task",
    "remind me tomorrow at 3pm to call mom",
    "HIGH (90-100)"
)

test_reminder(
    "Specific date and time",
    "remind me January 25th at 10:00am to submit the report",
    "HIGH (90-100)"
)

test_reminder(
    "Clear relative time",
    "remind me in 2 hours to check the oven",
    "HIGH (90-100)"
)

test_reminder(
    "Specific day and time",
    "remind me Saturday at 6pm to pick up dinner",
    "HIGH (90-100)"
)

test_reminder(
    "Every day recurring",
    "remind me every day at 8am to take vitamins",
    "HIGH (90-100)"
)

# ==========================================
# MEDIUM CONFIDENCE TESTS (borderline)
# ==========================================
print("\n\n" + "="*60)
print("SECTION 2: MEDIUM CONFIDENCE (borderline - may or may not confirm)")
print("="*60)

test_reminder(
    "Morning is slightly vague",
    "remind me Saturday morning to exercise",
    "MEDIUM (70-89)"
)

test_reminder(
    "Evening is slightly vague",
    "remind me tomorrow evening to call John",
    "MEDIUM (70-89)"
)

test_reminder(
    "Afternoon is slightly vague",
    "remind me Monday afternoon about the meeting",
    "MEDIUM (70-89)"
)

test_reminder(
    "End of day is vague",
    "remind me at end of day Friday to send the email",
    "MEDIUM (70-89)"
)

# ==========================================
# LOW CONFIDENCE TESTS (should ask for confirmation)
# ==========================================
print("\n\n" + "="*60)
print("SECTION 3: LOW CONFIDENCE (should ask for confirmation)")
print("="*60)

test_reminder(
    "Vague time - next week",
    "remind me sometime next week about the thing",
    "LOW (50-69)"
)

test_reminder(
    "Vague time - later",
    "remind me later to do that thing we talked about",
    "LOW (50-69)"
)

test_reminder(
    "Vague time - soon",
    "remind me soon about the project",
    "LOW (50-69)"
)

test_reminder(
    "No specific time given",
    "remind me to buy groceries",
    "LOW (50-69)"
)

test_reminder(
    "Vague everything",
    "set something for later about stuff",
    "LOW (below 50)"
)

test_reminder(
    "Ambiguous date reference",
    "remind me next time to bring the documents",
    "LOW (below 50)"
)

test_reminder(
    "Unclear task",
    "remind me tomorrow about you know what",
    "LOW (50-69)"
)

# ==========================================
# RELATIVE TIME TESTS
# ==========================================
print("\n\n" + "="*60)
print("SECTION 4: RELATIVE TIME REMINDERS")
print("="*60)

test_reminder(
    "Clear relative - minutes",
    "remind me in 30 minutes to switch laundry",
    "HIGH (90-100)"
)

test_reminder(
    "Clear relative - hours",
    "remind me in 3 hours to pick up kids",
    "HIGH (90-100)"
)

test_reminder(
    "Clear relative - days",
    "remind me in 5 days to follow up with client",
    "HIGH (90-100)"
)

test_reminder(
    "Vague relative - a bit",
    "remind me in a bit to check email",
    "LOW (50-69)"
)

test_reminder(
    "Vague relative - a while",
    "remind me in a while about the report",
    "LOW (50-69)"
)

# ==========================================
# RECURRING REMINDER TESTS
# ==========================================
print("\n\n" + "="*60)
print("SECTION 5: RECURRING REMINDERS")
print("="*60)

test_reminder(
    "Clear recurring - daily",
    "remind me every day at 9pm to lock the doors",
    "HIGH (90-100)"
)

test_reminder(
    "Clear recurring - weekly",
    "remind me every Monday at 10am for team standup",
    "HIGH (90-100)"
)

test_reminder(
    "Clear recurring - weekdays",
    "remind me every weekday at 7am to check calendar",
    "HIGH (90-100)"
)

test_reminder(
    "Vague recurring time",
    "remind me every Tuesday morning about the meeting",
    "MEDIUM (70-89)"
)

# ==========================================
# EDGE CASES
# ==========================================
print("\n\n" + "="*60)
print("SECTION 6: EDGE CASES")
print("="*60)

test_reminder(
    "Natural language with filler words",
    "hey can you remind me like tomorrow at maybe 2pm or so to call the doctor",
    "MEDIUM-LOW (60-75)"
)

test_reminder(
    "Multiple possible interpretations",
    "remind me Wednesday to prep for the thing on Thursday",
    "MEDIUM (70-89)"
)

test_reminder(
    "Abbreviations",
    "remind me tmrw @ 5 2 call bob",
    "MEDIUM (70-89)"
)

test_reminder(
    "Long detailed reminder",
    "remind me on February 14th at exactly 6:30pm to make reservations at the Italian restaurant on Main Street for our anniversary dinner",
    "HIGH (90-100)"
)

print("\n\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
print("\nSummary:")
print("- HIGH CONFIDENCE: Should create reminder immediately")
print("- LOW CONFIDENCE: Should ask 'Is that right?' before creating")
print("- Current threshold: 70 (configurable via settings)")
print("\nNote: The AI's actual confidence scores may vary from expected.")
print("This test helps calibrate whether the threshold is appropriate.")
