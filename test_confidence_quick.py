#!/usr/bin/env python
"""Quick test with threshold=95 to verify confirmation system works"""

import requests
import re
import time

API_URL = "http://localhost:8000/sms"
TEST_PHONE = "+15551234999"

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

print("="*60)
print("QUICK CONFIDENCE TEST (threshold=95)")
print("="*60)
print("With threshold at 95, most reminders should trigger confirmation\n")

tests = [
    ("Clear reminder", "remind me tomorrow at 3pm to call mom"),
    ("Vague task", "remind me tomorrow at 2pm about the thing"),
    ("Relative time", "remind me in 1 hour to check email"),
    ("Recurring", "remind me every day at 9am to exercise"),
]

for desc, msg in tests:
    print(f"\nTEST: {desc}")
    print(f"Input: '{msg}'")
    response = send_message(msg)
    safe_print(f"Response: {response[:250]}")

    if "Is that right?" in response or "Reply YES" in response:
        print("RESULT: LOW CONFIDENCE - Confirmation requested!")
        # Say no to cancel
        time.sleep(1)
        cancel_resp = send_message("no")
        safe_print(f"Cancel response: {cancel_resp[:100]}")
    elif "I'll remind you" in response or "Got it!" in response:
        print("RESULT: HIGH CONFIDENCE (95+) - Created immediately")
    else:
        print("RESULT: Other response")

    time.sleep(1.5)

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
