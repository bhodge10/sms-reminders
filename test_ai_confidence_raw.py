#!/usr/bin/env python
"""Test to see raw AI confidence scores"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from services.ai_service import process_with_ai

# Test messages
test_messages = [
    "remind me tomorrow at 3pm to call mom",
    "remind me tomorrow at 2pm about the thing",
    "remind me sometime next week about stuff",
    "remind me at 5pm about you know what",
    "remind me in a bit to check something",
]

print("="*60)
print("RAW AI CONFIDENCE SCORES")
print("="*60)

# Simple context for test
phone = "+15551234999"
context = {
    'first_name': 'Test',
    'timezone': 'America/Los_Angeles'
}

for msg in test_messages:
    print(f"\nInput: '{msg}'")
    print("-"*40)

    response = process_with_ai(msg, phone, context)

    print(f"Action: {response.get('action')}")
    print(f"Confidence: {response.get('confidence', 'NOT RETURNED')}")

    # Show relevant fields based on action
    action = response.get('action')
    if action == 'reminder':
        print(f"Date: {response.get('reminder_date')}")
        print(f"Text: {response.get('reminder_text')}")
    elif action == 'reminder_relative':
        print(f"Offset: mins={response.get('offset_minutes')}, days={response.get('offset_days')}")
        print(f"Text: {response.get('reminder_text')}")
