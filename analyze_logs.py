"""
Analyze user conversation logs from the database to find:
1. Conversations that may have had issues
2. Common patterns/phrasings to add to AI accuracy tests
3. Edge cases we haven't tested yet
"""

import os
import sys

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env.test')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)

def analyze_logs():
    """Analyze conversation logs for patterns and issues."""
    conn = get_connection()
    cur = conn.cursor()

    print("=" * 60)
    print("USER INTERACTION ANALYSIS")
    print("=" * 60)

    # Get total log count
    cur.execute("SELECT COUNT(*) FROM logs")
    total_logs = cur.fetchone()[0]
    print(f"\nTotal logged interactions: {total_logs}")

    # Get logs with issues (success = false or flagged in conversation_analysis)
    cur.execute("""
        SELECT COUNT(*) FROM logs WHERE success = false
    """)
    failed_count = cur.fetchone()[0]
    print(f"Failed interactions: {failed_count}")

    # Get flagged conversations
    cur.execute("SELECT COUNT(*) FROM conversation_analysis")
    flagged_count = cur.fetchone()[0]
    print(f"Flagged for analysis: {flagged_count}")

    # Get recent user messages with their intents
    print("\n" + "=" * 60)
    print("RECENT USER MESSAGES (last 100)")
    print("=" * 60)

    cur.execute("""
        SELECT message_in, message_out, intent, success, created_at
        FROM logs
        WHERE message_in IS NOT NULL AND message_in != ''
        ORDER BY created_at DESC
        LIMIT 100
    """)
    logs = cur.fetchall()

    intent_counts = defaultdict(int)
    for log in logs:
        msg_in = log[0] or ""
        msg_out = log[1] or ""
        intent = log[2] or "unknown"
        success = log[3]
        created = log[4]

        intent_counts[intent] += 1

        # Only show non-success or interesting interactions
        if not success or intent in ['unknown', 'error']:
            print(f"\n[{created}] Intent: {intent} | Success: {success}")
            print(f"  IN:  {msg_in[:100]}")
            print(f"  OUT: {msg_out[:100]}")

    print("\n" + "=" * 60)
    print("INTENT DISTRIBUTION")
    print("=" * 60)
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
        print(f"  {intent}: {count}")

    # Get flagged issues from conversation_analysis
    print("\n" + "=" * 60)
    print("FLAGGED ISSUES (conversation_analysis)")
    print("=" * 60)

    cur.execute("""
        SELECT ca.issue_type, ca.severity, ca.ai_explanation, ca.created_at, l.message_in, l.message_out
        FROM conversation_analysis ca
        LEFT JOIN logs l ON ca.log_id = l.id
        ORDER BY ca.created_at DESC
        LIMIT 50
    """)
    issues = cur.fetchall()

    if issues:
        for issue in issues:
            print(f"\n[{issue[3]}] {issue[0]} (severity: {issue[1]})")
            print(f"  Explanation: {issue[2][:200] if issue[2] else 'N/A'}")
            print(f"  User said: {issue[4][:100] if issue[4] else 'N/A'}")
            print(f"  Bot replied: {issue[5][:100] if issue[5] else 'N/A'}")
    else:
        print("No flagged issues found.")

    # Get unique user message patterns for test cases
    print("\n" + "=" * 60)
    print("UNIQUE MESSAGE PATTERNS FOR TEST CASES")
    print("=" * 60)

    cur.execute("""
        SELECT DISTINCT message_in, intent
        FROM logs
        WHERE message_in IS NOT NULL
        AND message_in != ''
        AND LENGTH(message_in) > 5
        ORDER BY created_at DESC
        LIMIT 200
    """)
    unique_messages = cur.fetchall()

    # Group by intent for easier review
    by_intent = defaultdict(list)
    for msg, intent in unique_messages:
        if msg and intent:
            by_intent[intent].append(msg)

    for intent, messages in sorted(by_intent.items()):
        print(f"\n{intent.upper()}:")
        for msg in messages[:10]:  # Show first 10 per intent
            print(f"  - {msg[:80]}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    analyze_logs()
