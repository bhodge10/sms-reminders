#!/usr/bin/env python
"""Test the specific critical fixes we made"""

import requests
import re
import time

API_URL = "http://localhost:8000/sms"
TEST_PHONE = "+15551238888"  # Another fresh number

def parse_twiml_response(xml_text):
    match = re.search(r'<Message>(.*?)</Message>', xml_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return xml_text

def safe_print(text):
    """Print with emoji-safe encoding for Windows console"""
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

print("\n=== CRITICAL FIX TESTS ===\n")

# Test 1: Daily summary false positive (was Test 2)
print("TEST 1: Daily summary false positive")
print("Input: 'remind me tomorrow at 10am to take my vitamins'")
response = send_message("remind me tomorrow at 10am to take my vitamins")
safe_print(f"Response: {response[:200]}")
# Check if a reminder was created (not just set daily summary time)
if "I'll remind you" in response and "10:00 AM" in response:
    print("STATUS: PASSED - Correctly created reminder!")
elif "daily summary" in response.lower() and "I'll remind you" not in response:
    print("STATUS: FAILED - Misinterpreted as daily summary setting")
else:
    print("STATUS: CHECK - Unexpected response")
# Answer the first-action prompt to clear state
time.sleep(1)
send_message("no")
time.sleep(2)

# Test 2: "every day" not recognized as recurring (was Test 29)
print("\nTEST 2: 'every day' recurring recognition")
print("Input: 'remind me every day at 8am to take medication'")
response = send_message("remind me every day at 8am to take medication")
safe_print(f"Response: {response[:200]}")
if "every day" in response.lower() or "daily" in response.lower():
    print("STATUS: PASSED - Correctly recognized as recurring!")
elif "January" in response and "8:00 AM" in response:
    print("STATUS: FAILED - Created one-time reminder instead of recurring")
else:
    print("STATUS: CHECK - Unexpected response")
time.sleep(2)

# Test 3: Time ignored in complex date (was Test 13)
print("\nTEST 3: Time extraction in complex date")
print("Input: 'remind me December 31st 2026 at 11pm for new years countdown'")
response = send_message("remind me December 31st 2026 at 11pm for new years countdown")
safe_print(f"Response: {response[:200]}")
if "What time" in response:
    print("STATUS: FAILED - Still asking for time when 11pm was specified")
elif "11:00 PM" in response or "11pm" in response.lower():
    print("STATUS: PASSED - Correctly extracted time!")
else:
    print("STATUS: CHECK - Unexpected response")
time.sleep(2)

# Test 4: Memory timezone (was Test 26)
print("\nTEST 4: Memory timezone display")
# First clear any pending state
send_message("cancel")
time.sleep(1)
print("Input: 'remember that my wifi password is TestPass123'")
response = send_message("remember that my wifi password is TestPass123")
safe_print(f"Response: {response[:150]}")
time.sleep(2)
print("Input: 'what is my wifi password?'")
response = send_message("what is my wifi password?")
safe_print(f"Response: {response[:200]}")
# Check if the date matches today (Jan 17) not tomorrow (Jan 18)
if "January 17" in response:
    print("STATUS: PASSED - Correct date displayed!")
elif "January 18" in response:
    print("STATUS: FAILED - Still showing wrong date")
else:
    print("STATUS: CHECK - Date not visible in response")

print("\n=== TESTS COMPLETE ===")
