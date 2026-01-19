#!/usr/bin/env python
"""Run Phase 1 (onboarding) tests only"""

import json
import requests
import time
from datetime import datetime
import re

API_URL = "http://localhost:8000/sms"
TEST_PHONE = "+15559876547"  # Fresh number to test onboarding

def parse_twiml_response(xml_text):
    match = re.search(r'<Message>(.*?)</Message>', xml_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return xml_text

def send_message(message):
    try:
        response = requests.post(
            API_URL,
            data={"Body": message, "From": TEST_PHONE},
            timeout=60
        )
        return {
            "status_code": response.status_code,
            "parsed_response": parse_twiml_response(response.text),
            "error": None
        }
    except Exception as e:
        return {"status_code": None, "parsed_response": None, "error": str(e)}

# Phase 1: Onboarding tests
onboarding_tests = [
    ("START", "Should trigger welcome message and ask for name"),
    ("Test User", "Should accept name and ask for email"),
    ("testuser@example.com", "Should accept email and ask for ZIP code"),
    ("90210", "Should complete onboarding and confirm timezone (Pacific)"),
]

print(f"=== PHASE 1: ONBOARDING TESTS ===")
print(f"Time: {datetime.now().isoformat()}")
print(f"Phone: {TEST_PHONE}")
print("-" * 60)

results = []
for i, (message, expected) in enumerate(onboarding_tests, 1):
    print(f"\n[{i}/4] Sending: {message}")
    print(f"       Expected: {expected}")

    response = send_message(message)

    if response["error"]:
        print(f"       ERROR: {response['error']}")
        status = "ERROR"
    else:
        # Clean response for display
        resp_text = response["parsed_response"] or ""
        resp_preview = resp_text[:150].encode('ascii', 'replace').decode('ascii')
        print(f"       Response: {resp_preview}...")

        # Basic pass/fail check
        if "something went wrong" in resp_text.lower():
            status = "FAIL"
        elif i == 1 and "welcome" in resp_text.lower():
            status = "PASS"
        elif i == 1 and "first name" in resp_text.lower():
            status = "PASS"
        elif i == 2 and "email" in resp_text.lower():
            status = "PASS"
        elif i == 3 and "zip" in resp_text.lower():
            status = "PASS"
        elif i == 4 and ("pacific" in resp_text.lower() or "timezone" in resp_text.lower() or "all set" in resp_text.lower()):
            status = "PASS"
        else:
            status = "CHECK"

    print(f"       Status: {status}")
    results.append({"test": i, "message": message, "status": status, "response": response["parsed_response"]})
    time.sleep(2)

print("\n" + "=" * 60)
print("SUMMARY:")
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
check = sum(1 for r in results if r["status"] == "CHECK")
print(f"  PASS: {passed}")
print(f"  FAIL: {failed}")
print(f"  CHECK: {check}")

# Save results
with open("phase1_test_results.json", "w", encoding="utf-8") as f:
    json.dump({"timestamp": datetime.now().isoformat(), "results": results}, f, indent=2, ensure_ascii=False)
print("\nResults saved to phase1_test_results.json")
