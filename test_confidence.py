#!/usr/bin/env python
"""Test the confidence-based confirmation system"""

import requests
import re
import time

API_URL = "http://localhost:8000/sms"
TEST_PHONE = "+15551236666"  # Fresh number

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

# Onboard the user first
print("=== ONBOARDING ===")
safe_print("START -> " + send_message("START")[:80])
time.sleep(1)
safe_print("Name -> " + send_message("Test User")[:80])
time.sleep(1)
safe_print("Email -> " + send_message("test@example.com")[:80])
time.sleep(1)
safe_print("ZIP -> " + send_message("90210")[:80])
time.sleep(2)

# Skip first-action prompt
send_message("no")
time.sleep(1)

print("\n=== CONFIDENCE TESTS ===\n")

# Test 1: Clear reminder (should be high confidence, no confirmation needed)
print("TEST 1: Clear reminder - should create immediately")
print("Input: 'remind me tomorrow at 3pm to call mom'")
response = send_message("remind me tomorrow at 3pm to call mom")
safe_print(f"Response: {response[:200]}")
if "Is that right?" in response:
    print("RESULT: Asking for confirmation (low confidence)")
elif "I'll remind you" in response:
    print("RESULT: Created immediately (high confidence) - EXPECTED")
else:
    print("RESULT: Unexpected response")
time.sleep(2)

# Test 2: Try undo command
print("\nTEST 2: Undo command")
print("Input: 'undo'")
response = send_message("undo")
safe_print(f"Response: {response[:200]}")
if "Delete your most recent" in response:
    print("RESULT: Offered to delete recent reminder - WORKING")
    # Say no to keep it
    send_message("no")
    time.sleep(1)
elif "Nothing to undo" in response:
    print("RESULT: No recent reminder found")
else:
    print("RESULT: Unexpected response")
time.sleep(2)

# Test 3: Ambiguous reminder (might be low confidence)
print("\nTEST 3: Slightly ambiguous reminder")
print("Input: 'remind me sometime next week about the thing'")
response = send_message("remind me sometime next week about the thing")
safe_print(f"Response: {response[:200]}")
if "Is that right?" in response:
    print("RESULT: Asking for confirmation (low confidence) - EXPECTED for ambiguous")
    # Confirm it
    send_message("yes")
    time.sleep(1)
elif "I'll remind you" in response:
    print("RESULT: Created immediately (high confidence)")
elif "What time" in response:
    print("RESULT: Asking for time clarification")
else:
    print("RESULT: Unexpected response")

print("\n=== TESTS COMPLETE ===")
print("\nNote: Whether confirmations appear depends on AI confidence scores.")
print("The system is working if you see sensible responses to each test.")
