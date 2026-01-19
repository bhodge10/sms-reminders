#!/usr/bin/env python
"""Targeted test for confidence-based confirmation - requests with times but other ambiguity"""

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
    elif "What time" in response or "which day" in response.lower() or "Do you mean" in response:
        result = "NEEDS CLARIFICATION - Asking follow-up"
    else:
        result = "OTHER RESPONSE"

    print(f"RESULT: {result}")
    time.sleep(1.5)
    return result

print("="*60)
print("TARGETED CONFIDENCE TEST")
print("="*60)
print("Testing reminders WITH times but with other ambiguities")
print("(to trigger the confidence check rather than time clarification)")

# These all have specific times, so AI should try to parse them
# But they have other ambiguities that might cause low confidence

print("\n\n" + "="*60)
print("SECTION 1: Ambiguous task description (time is clear)")
print("="*60)

test_reminder(
    "Vague task 'the thing'",
    "remind me tomorrow at 2pm about the thing",
    "SHOULD BE LOW - what thing?"
)

test_reminder(
    "Very vague task 'it'",
    "remind me at 5pm today about it",
    "SHOULD BE LOW - about what?"
)

test_reminder(
    "Unclear reference",
    "remind me at 3pm tomorrow to do you know what",
    "SHOULD BE LOW - unclear task"
)

test_reminder(
    "Ambiguous person reference",
    "remind me Monday at 10am to call them about the project",
    "SHOULD BE LOW - who is them?"
)

print("\n\n" + "="*60)
print("SECTION 2: Potentially confusing date references")
print("="*60)

test_reminder(
    "Next vs this - potential confusion",
    "remind me next Saturday at noon to go shopping",
    "MEDIUM - next Saturday could mean different things"
)

test_reminder(
    "This coming vs just 'this'",
    "remind me this Friday at 3pm for the appointment",
    "MEDIUM - which Friday exactly?"
)

test_reminder(
    "Ambiguous 'the 15th' (which month?)",
    "remind me on the 15th at 9am to pay the bill",
    "SHOULD BE LOW - which month?"
)

test_reminder(
    "End of month (ambiguous which month)",
    "remind me at end of month at 5pm to submit reports",
    "SHOULD BE LOW - which month?"
)

print("\n\n" + "="*60)
print("SECTION 3: Complex multi-part requests")
print("="*60)

test_reminder(
    "Multiple things in one request",
    "remind me tomorrow at 4pm to call john and also email sarah about the meeting and pick up groceries",
    "MEDIUM - multiple tasks, parsing correctly?"
)

test_reminder(
    "Nested time references",
    "remind me at 2pm tomorrow that I have a meeting the day after at 3pm",
    "COULD BE CONFUSING - which time is the reminder?"
)

test_reminder(
    "Conditional reminder",
    "remind me at 6pm to call mom if I haven't heard back by then",
    "MEDIUM - conditional logic"
)

print("\n\n" + "="*60)
print("SECTION 4: Typos and informal language")
print("="*60)

test_reminder(
    "Typos in the message",
    "remnd me tmrw at 2pm to cal the dctr",
    "MEDIUM - can AI parse this correctly?"
)

test_reminder(
    "All lowercase no punctuation",
    "remind me sat at 4 to get gas",
    "MEDIUM - informal style"
)

test_reminder(
    "Mixed up word order",
    "at 3pm tomorrow remind me to pick up package",
    "MEDIUM - unusual word order"
)

print("\n\n" + "="*60)
print("SECTION 5: Edge case times")
print("="*60)

test_reminder(
    "Midnight ambiguity",
    "remind me at midnight to take medicine",
    "MEDIUM - midnight tonight or tomorrow?"
)

test_reminder(
    "Noon ambiguity",
    "remind me noon Monday about lunch",
    "HIGH - should be clear"
)

test_reminder(
    "Military time",
    "remind me at 1400 tomorrow to join the call",
    "MEDIUM - does AI parse 24hr time?"
)

test_reminder(
    "Unusual time format",
    "remind me at half past 3 tomorrow to leave",
    "MEDIUM - natural language time"
)

print("\n\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
print("\nThese tests include clear times but other ambiguities.")
print("If confidence system is working, some should trigger confirmation.")
