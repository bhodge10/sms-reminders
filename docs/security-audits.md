# Security Audit History

## Round 4 — Trial, Stripe, and Data Safety (Feb 2026)
Narrow-scope audit focused on three questions: (1) Do trial messages fire correctly? (2) Does UPGRADE flow work end-to-end? (3) Any critical data-loss/double-billing/cancellation bugs?

**Phase 1 (Critical — PR #132):**
- **Trial flag whitelist:** Added 8 trial lifecycle flags (`trial_warning_7d_sent`, `trial_warning_1d_sent`, `trial_warning_0d_sent`, `mid_trial_reminder_sent`, `day_3_nudge_sent`, `post_trial_reengagement_sent`, `post_trial_14d_sent`, `winback_30d_sent`) to `ALLOWED_USER_FIELDS` in `models/user.py`. Without these, `create_or_update_user()` silently dropped the flags, causing every trial message to repeat daily.
- **Day 0 premium_status reset:** Added `create_or_update_user(phone_number, premium_status='free')` in the Day 0 handler of `check_trial_expirations` so post-trial tasks (Day 3, Day 14, Day 30) can find expired users.
- **TCPA opted_out filter:** Added `(opted_out IS NULL OR opted_out = FALSE)` to `check_trial_expirations` and `send_mid_trial_value_reminders` SQL queries to honor SMS opt-out.
- **Premium subscriber filter:** Added `(stripe_subscription_id IS NULL OR subscription_status != 'active')` to `check_trial_expirations` so paying subscribers don't receive "your trial is expiring" messages.
- **Double-billing prevention:** Added `stripe.Subscription.list(customer=id, status='active')` check in `create_checkout_session()` (`services/stripe_service.py`) before creating a new checkout, returning an error if the user already has an active subscription.

**Phase 2 (High/Medium — PR #133):**
- **CANCEL keyword handler:** Added `CANCEL SUBSCRIPTION` / `CANCEL PLAN` / `CANCEL PREMIUM` keyword handler in `main.py` that redirects users to `ACCOUNT` for the Stripe billing portal.
- **Connection pool safety:** Added `conn.rollback()` in `return_db_connection()` (`database.py`) before returning connections to the pool, preventing cascading failures from aborted transactions leaving connections in an error state.
- **Trial day-range checks:** Replaced all 7 exact-day comparisons in trial lifecycle tasks (`tasks/reminder_tasks.py`) with range checks to handle signup time-of-day edge cases where `timedelta.days` floor causes missed windows:
  - Day 7: `== 7` → `6 <= days_remaining <= 7`
  - Day 1: `== 1` → `0 < days_remaining <= 1`
  - Mid-trial Day 7: `!= 7` → `not (6 <= days_remaining <= 7)`
  - Day 3 nudge: `!= 3` → `not (2 <= days_in_trial <= 3)`
  - Post-trial Day 3: `!= 3` → `not (2 <= days_since_expiry <= 3)`
  - 14-day touchpoint: `!= 14` → `not (13 <= days_since_expiry <= 14)`

## Round 5 — Comprehensive Audit (Feb 2026)

### Critical Fixes (PR #146)
6 critical issues identified and fixed:

- **C1 — Duplicate SMS race condition:** `send_single_reminder` released the `FOR UPDATE` lock via `conn.commit()` before marking `sent=TRUE` on a separate connection. Fixed by keeping the lock and marking sent in a single atomic commit. Added a fresh-connection fallback with `CRITICAL` log level as last resort.
- **C2 — Trial SMS + flag atomicity:** Trial lifecycle tasks committed DB flag changes BEFORE sending SMS. If SMS failed, the flag was set but the user never received the message. Fixed by moving all state changes to AFTER SMS send, committed atomically.
- **C3 — Monitoring connection pool poisoning:** `return_monitoring_connection()` returned connections without rolling back aborted transactions. Fixed by adding `conn.rollback()` before `putconn()`.
- **C4 — Missing Celery task timeouts:** 22 Celery tasks lacked `time_limit`/`soft_time_limit`. Added appropriate timeouts to all tasks (60s–3600s).
- **C5 — PII exposure in admin API:** `/admin/stats` returned full phone numbers. Fixed by masking to `***-***-1234` format.
- **C6 — SQL injection in cost analytics:** `get_cost_analytics()` used f-string interpolation for `INTERVAL`. Fixed with `%s::interval` parameterized casting.

**Files changed:** `database.py`, `main.py`, `services/metrics_service.py`, `tasks/monitoring_tasks.py`, `tasks/reminder_tasks.py`

### High-Priority Fixes (PR #148)
11 issues fixed:

- **H1 — Bare except clauses:** Replaced 6 remaining bare `except:` with specific types across `main.py`, `admin_dashboard.py`, `services/reminder_service.py`.
- **H2 — XSS in admin changelog:** Added `html.escape()` on `title` and `description` in the public updates page.
- **H3 — Secrets printed to stdout:** `generate_keys()` no longer prints keys; returns them silently.
- **H4 — Silent decryption failures:** `safe_decrypt()` now logs `logger.warning` on failure.
- **H5 — Silent migration failures:** `init_db()` now distinguishes expected "already exists" errors from unexpected ones.
- **H6 — Broadcast checker crash recovery:** Added consecutive failure tracking (stops after 10), exponential backoff (60s→5min).
- **H7 — Daily summary SMS overflow:** Truncate to 1500 chars with "Text MY REMINDERS for full list" fallback.
- **H8 — Outbound SMS length validation:** `send_sms()` truncates messages exceeding Twilio's 1600-char limit.
- **H9 — Monitoring window overlap:** Changed interaction monitor from 24h to 4h analysis window.
- **H10 — Stale claims timeout:** Increased `release_stale_claims` from 5 to 15 minutes.
- **H11 — SQL identifier quoting:** Dynamic table/column names now use `psycopg2.sql.Identifier()`.

**Files changed:** `admin_dashboard.py`, `celery_config.py`, `database.py`, `main.py`, `services/reminder_service.py`, `services/sms_service.py`, `tasks/reminder_tasks.py`, `utils/encryption.py`

### Medium-Priority Fixes (PR #150)
10 issues fixed:

- **M1 — Hardcoded trial days:** Replaced hardcoded `14` with `FREE_TRIAL_DAYS` constant.
- **M2/M9 — Session ID validation:** Added regex validation on `/payment/success` and `/api/payment-info`.
- **M3 — TCPA opt-out keywords:** Added STOPALL, UNSUBSCRIBE, END, QUIT handling alongside STOP.
- **M4/M10 — PII in admin delete:** Masked phone numbers in admin user deletion log and API response.
- **M5 — Public endpoint rate limiting:** Added IP-based rate limiting (5 req/5 min) on `/api/signup` and `/api/contact`.
- **M6 — Auth failure rate limiting:** Added brute force protection (5 failures/5 min lockout) on admin auth.
- **M7 — CS portal audit logging:** Added logging for credential type and failed attempts.
- **M8 — Webhook idempotency:** Added MessageSid deduplication in SMS webhook.

**Files changed:** `main.py`, `admin_dashboard.py`, `cs_portal.py`, `tasks/reminder_tasks.py`

### Low-Priority Fixes (PR #152)
4 issues fixed:

- **L1 — Admin error message sanitization:** Replaced 48 instances of `detail=str(e)` with `detail="Internal server error"`.
- **L2 — BETA_MODE default:** Changed default from `"true"` to `"false"`.
- **L3 — Dynamic SQL field whitelist:** Added whitelist validation for dynamic column names in trial tasks.
- **L4 — Contact form sanitization:** Applied `sanitize_text()` to `/api/contact` message body.

**Files changed:** `admin_dashboard.py`, `config.py`, `main.py`, `tasks/reminder_tasks.py`

## Round 6 — Final Security Pass (Feb 2026)
2 high, 4 medium, 2 low issues. No critical vulnerabilities.

### High-Priority (PR #164)

- **H1 — HTTP Security Headers Middleware:** Added `SecurityHeadersMiddleware` in `main.py` that sets 7 headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Strict-Transport-Security`, `Referrer-Policy`, `Permissions-Policy`, and `Content-Security-Policy`.
- **H2 — Consolidated Auth Rate Limiting:** Extracted auth rate limiting into shared `utils/auth.py` module. Applied brute-force protection to all 4 auth endpoints.

**Files changed:** `main.py`, `admin_dashboard.py`, `monitoring_dashboard.py`, `cs_portal.py`, `utils/auth.py` (new)

### Medium/Low-Priority (PR #165)

- **M1 — Stripe Webhook Exception Leak:** `str(e)` → `"Internal server error"`.
- **M2 — Admin Duplicate Reminders Exception Leak:** `detail=str(e)` → `detail="Internal server error"`.
- **M3 — F-string SQL → psycopg2.sql.Identifier():** `create_or_update_user()` converted to parameterized SQL.
- **M4 — Webhook Idempotency Full-Clear Bug:** Replaced `_processed_message_sids.clear()` with TTL-based eviction.
- **L1 — Bare except in Test File:** `except:` → `except Exception:`.
- **L2 — Unpinned Dependency Upper Bounds:** Added `<major+1.0.0` caps to all `>=`-only deps in `requirements-prod.txt`.

**Files changed:** `main.py`, `models/user.py`, `tests/test_background_tasks.py`, `requirements-prod.txt`
