"""
Shared auth rate limiting utilities.
Prevents brute-force attacks on all authenticated endpoints.
"""

import time
from collections import defaultdict
from fastapi import HTTPException
from utils.validation import log_security_event

# Auth failure rate limiting (per username)
_auth_fail_store = defaultdict(list)
_AUTH_FAIL_LIMIT = 5  # max failures per window
_AUTH_FAIL_WINDOW = 300  # 5 minute lockout window


def check_auth_rate_limit(username: str) -> bool:
    """Check if username has exceeded auth failure rate limit. Returns True if allowed."""
    current_time = time.time()
    window_start = current_time - _AUTH_FAIL_WINDOW
    _auth_fail_store[username] = [ts for ts in _auth_fail_store[username] if ts > window_start]
    return len(_auth_fail_store[username]) < _AUTH_FAIL_LIMIT


def record_auth_failure(username: str):
    """Record an auth failure for rate limiting."""
    _auth_fail_store[username].append(time.time())


def enforce_auth_rate_limit(username: str, endpoint: str):
    """Check rate limit and raise 429 if exceeded. Call before credential verification."""
    if not check_auth_rate_limit(username):
        log_security_event("AUTH_LOCKOUT", {"username": username, "endpoint": endpoint})
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Try again in 5 minutes.",
        )
