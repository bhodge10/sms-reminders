# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Remyndrs is an SMS-based AI memory and reminder service built with Python/FastAPI. Users interact entirely via SMS to store memories, create reminders, and manage to-do lists using natural language.

**Stack:** Python 3.11.9, FastAPI, PostgreSQL, Celery + Redis (Upstash), OpenAI GPT-4o-mini, Twilio SMS, Stripe billing

## Git Workflow

**Branching model:** Feature branches off `main`. No long-lived staging branch.

**Starting a session:**
```bash
git checkout main && git pull origin main
```

**Making changes:**
```bash
git checkout -b feature/short-description
# ... work and commit ...
git push -u origin feature/short-description
# Open PR → merge to main → delete branch
```

**Ending a session:** Push your feature branch so work isn't lost.

**Important:** Never deploy directly to Render — always push to git and let auto-deploy handle it.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
uvicorn main:app --reload

# Run Celery worker (processes reminder tasks)
celery -A celery_app worker --loglevel=info

# Run Celery Beat (schedules periodic tasks)
celery -A celery_app beat --loglevel=info

# Run all tests
python run_tests.py

# Run quick tests (skip slow)
python run_tests.py --quick

# Run specific test categories
python run_tests.py --onboarding
python run_tests.py --reminders
python run_tests.py --lists
python run_tests.py --memories
python run_tests.py --edge
python run_tests.py --tasks
python run_tests.py --scenarios

# Run with coverage
python run_tests.py --coverage

# Run single test
pytest tests/test_reminders.py::TestReminderCreation::test_reminder_with_specific_time
```

## Architecture

### Request Flow
```
SMS → Twilio webhook (/sms) → main.py validates → ai_service.py processes with OpenAI
  → models/*.py persists to PostgreSQL → sms_service.py sends confirmation
  → Celery Beat (every 30s) checks due reminders → sends at user's timezone
```

### Layered Structure
- **HTTP Layer:** `main.py` (routes), `admin_dashboard.py` (admin metrics/broadcast), `cs_portal.py` (customer support)
- **Route Handlers:** `routes/handlers/` - modular handlers for reminders, lists, memories, pending states
- **Business Logic:** `services/` - AI processing, payments, onboarding, metrics
- **Data Access:** `models/` - user, reminder, memory, list operations (with type hints)
- **Background Tasks:** `tasks/reminder_tasks.py` - Celery periodic jobs
- **Utils:** timezone conversions, encryption, input validation, `db_helpers.py` for encryption queries

### Key Files
| File | Purpose |
|------|---------|
| `main.py` | FastAPI routes, Twilio webhook handling |
| `services/ai_service.py` | OpenAI integration, prompt engineering |
| `models/reminder.py` | Reminder CRUD, recurring reminder logic |
| `models/user.py` | User management, encryption support |
| `tasks/reminder_tasks.py` | Celery tasks (reminder checking, daily summaries) |
| `config.py` | Environment variables, tier limits, constants |
| `database.py` | PostgreSQL connection pooling, schema init |
| `routes/handlers/` | Modular handlers for reminders, lists, memories |
| `utils/db_helpers.py` | Encryption-aware database query helpers |

### Database Tables
`users`, `reminders`, `recurring_reminders`, `memories`, `lists`, `list_items`, `interactions`, `support_tickets`, `broadcast_messages`, `conversation_flags`

## Deployment

Deployed on Render with three services:
1. **sms-reminders-api** - FastAPI web service
2. **sms-reminders-worker** - Celery worker
3. **sms-reminders-beat** - Celery Beat scheduler

Config in `render.yaml`. Auto-deploys on push to main.

## Testing

Tests use `ConversationSimulator` to simulate SMS interactions without real messages. Key fixtures:
- `simulator` - simulates user SMS interactions
- `sms_capture` - captures outbound SMS for verification
- `ai_mock` - mocks AI responses for predictable testing
- `onboarded_user` - pre-created test user (auto-cleaned)
- `mock_datetime` - time mocking for reminder tests

Test phone number: `+15559876543`

### Test Safety
Tests are configured to **never hit real Twilio or OpenAI APIs**:
- `conftest.py` has autouse fixtures that mock all SMS/AI calls
- `sms_service.py` detects test environment and blocks real Twilio calls
- Use `.env.test` with `ENVIRONMENT=test` and fake API keys
- Run tests with: `py -3 -m pytest tests/test_onboarding.py -v`

## Key Patterns

### Timezone Handling
All timestamps stored in UTC, converted to user timezone on display. User timezone determined during onboarding from ZIP code.

### Reminder Atomicity
Uses `SELECT FOR UPDATE SKIP LOCKED` for distributed reminder claiming. Stale tasks released every 5 minutes if worker crashes.

### Subscription Tiers
- **Free:** 2 reminders/day, 5 lists, 10 items/list, 5 memories
- **Premium:** Unlimited reminders, 20 lists, 30 items/list, recurring reminders
- **Family:** Premium features for 4-10 members

### Low-Confidence Reminder Confirmation Flow
When AI confidence is below threshold, reminders enter a pending confirmation state stored in `pending_reminder_confirmation` on the user record. Two code paths handle this:
- **Pending data storage:** `routes/handlers/reminders.py` stores pending JSON (action type, text, datetime, offsets, confidence)
- **Confirmation handling:** `main.py` (search `pending_confirmation`) processes YES/NO responses and calls `save_reminder_with_local_time()`

**Important:** `save_reminder_with_local_time()` requires 5 positional args: `(phone_number, reminder_text, reminder_date_utc, local_time, timezone)`. The `local_time` param is HH:MM format and `reminder_date` must be UTC. For relative reminders, the pre-calculated UTC datetime and local_time should be stored in pending data to avoid time drift.

### Field Encryption
Optional AES-256-GCM encryption for PII (names, emails). Enabled via `ENCRYPTION_KEY` and `HASH_KEY` env vars.

## Environment Variables

Required: `OPENAI_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `DATABASE_URL`

Optional: `UPSTASH_REDIS_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ENCRYPTION_KEY`, `HASH_KEY`, `STRIPE_*` keys, `SMTP_*` for email, `ANTHROPIC_API_KEY` (for Agent 4 AI file identification)

## Rate Limiting

15 messages per 60-second window per user (configurable in `config.py`).

## Multi-Agent Monitoring System

Automated issue detection and health tracking for the SMS service.

### Dashboard
- **URL:** `/admin/monitoring`
- Visual dashboard showing health score, open issues, patterns, and trends
- Click any issue to see full message context (user message + bot response)
- "Mark False Positive" button to dismiss non-issues

### Four Agents
1. **Agent 1 - Interaction Monitor** (`agents/interaction_monitor.py`)
   - Detects anomalies: user confusion, parsing failures, error responses, timezone issues
   - Scans `logs` table for patterns indicating problems

2. **Agent 2 - Issue Validator** (`agents/issue_validator.py`)
   - Validates issues from Agent 1, filters false positives
   - Optional AI analysis with GPT-4o-mini (`use_ai=True`)
   - Identifies recurring patterns

3. **Agent 3 - Resolution Tracker** (`agents/resolution_tracker.py`)
   - Calculates health score (0-100)
   - Tracks issue resolutions and detects regressions
   - Generates weekly reports

4. **Agent 4 - Fix Planner** (`agents/fix_planner.py`)
   - Analyzes validated, unresolved issues
   - Identifies affected source files based on issue type/pattern
   - Extracts relevant code context
   - Generates paste-ready Claude Code prompts for fixes
   - Optional AI file identification with Claude API (`--ai` flag)

### Celery Schedule (automatic)
- **Hourly:** Critical issue check
- **Every 4 hours:** Agent 1 (interaction monitor)
- **Every 6 hours:** Agent 2 (issue validator)
- **Daily 6 AM UTC:** Full pipeline with AI
- **Weekly Monday 8 AM UTC:** Weekly report

### Manual Triggers
- Dashboard "Run Full Pipeline" button
- API: `GET /admin/pipeline/run?hours=24`
- Agent 4: `python -m agents.fix_planner --issue 123` or `python agents/run_fix_planner.py`
- Full pipeline with fix planner: `python agents/run_pipeline.py --fix-planner`

### Alerts
Configured via dashboard Alert Settings section:
- **Teams:** Requires `TEAMS_WEBHOOK_URL` env var
- **Email:** Requires `SMTP_*` env vars and recipient list
- **SMS:** For critical issues only (health < 50)

### Database Tables
`monitoring_issues`, `monitoring_runs`, `issue_patterns`, `issue_pattern_links`, `validation_runs`, `issue_resolutions`, `pattern_resolutions`, `health_snapshots`, `fix_proposals`, `fix_proposal_runs`

---

## UX Improvement Roadmap

**Overall UX Score: B+ (82/100)** - Based on comprehensive user journey analysis (Jan 2026)

### User Journey Map

#### 1. Onboarding Flow (Grade: A-)
**Journey:** Hi → Name → Last Name → Email → ZIP → Complete (14-day trial)

**Strengths:**
- Progressive disclosure (one question at a time)
- Flexible input (accepts "John Smith" as full name)
- Clear validation with helpful errors
- Safety valves (HELP, CANCEL, RESTART, SKIP)
- Immediate value (auto-creates first memory, sends VCF)
- Generous 14-day trial with no credit card

**Issues:**
- ❌ **CRITICAL:** No welcome message explaining what Remyndrs is
- ⚠️ **MODERATE:** Skip friction (persuasive text feels pushy)
- ⚠️ **MODERATE:** No progress indicator shown proactively

#### 2. Premium Upgrade Flow (Grade: C+)
**Journey:** UPGRADE → Pricing display → PREMIUM/FAMILY → Stripe link → Payment → Activated

**Strengths:**
- Clear pricing (monthly/annual options)
- Stripe Checkout (trusted, secure)
- Immediate premium access

**Issues:**
- ❌ **CRITICAL:** No trial end warning (silent downgrade on day 15)
- ❌ **CRITICAL:** Link-only upgrade (no fallback if link fails)
- ⚠️ **MODERATE:** No value reminder before purchase

#### 3. Downgrade/Cancellation Flow (Grade: B-)
**Strengths:**
- Data preservation (reminders/memories kept)
- Self-service Stripe Customer Portal
- Clear SMS confirmation

**Issues:**
- ❌ **CRITICAL:** No exit interview or cancellation feedback
- ⚠️ **MODERATE:** Unclear downgrade impact on existing data
- ⚠️ **MODERATE:** No win-back attempt after cancellation

#### 4. Account Management (Grade: C)
**Issues:**
- ❌ **CRITICAL:** No account overview command (can't see status, tier, usage)
- ❌ **CRITICAL:** No usage visibility (free users don't know they're at 1/2 reminders)

---

### Prioritized Action Plan

#### PHASE 1: Critical Fixes (Week 1)
**Impact: High | Effort: Low | Expected: +15% trial conversion**

##### 1. Trial Expiration Warnings (2 hours)
**Files:** `tasks/reminder_tasks.py`, add database column `trial_warning_sent`

```python
# Add Celery scheduled tasks for:
# Day 7:  "You have 7 days left in your Premium trial! ⏰
#          Text UPGRADE to keep unlimited reminders."
# Day 13: "Tomorrow is your last day of Premium trial.
#          Text UPGRADE now to continue unlimited features!"
# Day 14: "Your Premium trial has ended. You're now on the free plan
#          (2 reminders/day). Text UPGRADE anytime!"
```

##### 2. Welcome Message (15 minutes)
**File:** `services/onboarding_service.py:121`

```python
# BEFORE asking for name, add:
"Welcome to Remyndrs! 👋 I'm your AI-powered reminder assistant.
I'll help you remember anything—from daily tasks to important dates.

Let's get you set up in under a minute! What's your first name?"
```

##### 3. Usage Counter for Free Users (1 hour)
**Files:** `main.py` (reminder confirmation), `services/tier_service.py`

```python
# After creating reminder (free tier):
"✓ Reminder saved! (1 of 2 today)"

# When hitting limit:
"You've used your 2 free reminders today. ⏰
Resets at midnight, or text UPGRADE for unlimited!"
```

#### PHASE 2: Value & Visibility (Week 2)
**Impact: Medium-High | Effort: Medium | Expected: +10% retention**

##### 4. Account Status Command (3 hours)
**Files:** `main.py`, create new handler in `routes/handlers/account.py`

```python
# Add INFO or STATUS command:
"""
📊 Your Account

Plan: Premium ($6.99/month)
Member since: Jan 15, 2024
Next billing: Feb 15, 2024

This month:
• 47 reminders created
• 3 active lists
• 12 memories saved

Text ACCOUNT to manage billing
"""
```

##### 5. Mid-Trial Value Reminder (1 hour)
**Files:** `tasks/reminder_tasks.py`

```python
# Day 7 of trial:
"You're halfway through your Premium trial! 🎉

So far you've created 12 reminders and 2 lists.
After trial: only 2 reminders/day on free plan.

Text UPGRADE to keep unlimited access!"
```

#### PHASE 3: Feedback & Retention (Week 3)
**Impact: Medium | Effort: Low-Medium | Expected: Better product insights**

##### 6. Cancellation Feedback Loop (2 hours)
**Files:** `services/stripe_service.py` (webhook handler), add database column `cancellation_reason`

```python
# After Stripe cancellation webhook:
"Sorry to see you go! 😢

Quick question: Why did you cancel?
1. Too expensive
2. Not using it enough
3. Missing a feature
4. Other reason

(Reply with number or SKIP)"
```

##### 7. Win-Back Campaign (2 hours)
**Files:** `tasks/reminder_tasks.py` (30-day task)

```python
# 30 days after cancel:
"Hey! We've missed you at Remyndrs.

Since you left, we've added:
• Improved AI accuracy
• Faster response times
• New list features

Want to come back? Text UPGRADE for 20% off your first month!"
```

#### PHASE 4: Polish & Optimization (Ongoing)

##### 8. Conversational Tone Improvements
- Replace robotic language with warm, friendly tone
- Add appropriate emoji (✓ ⏰ 📊 🎉 😊)
- Shorten confirmation messages
- Add personality to error messages

**Examples:**
```
❌ "Your account has been reset. Let's start over!"
✅ "All set! Let's start fresh 😊"

❌ "Feedback received. Thank you!"
✅ "Thanks for the feedback! We really appreciate it."

❌ "You've reached your daily limit of 2 reminders."
✅ "Oops, you've hit your 2 reminders for today. Want unlimited? Text UPGRADE!"
```

##### 9. Progress Indicators
- Show "Step X of 4" in all onboarding prompts
- Add progress confirmation for multi-step workflows
- Clearer action feedback

##### 10. Export Before Delete
- Offer to email data export before deletion
- 24-hour soft delete with UNDO option
- Clear communication about what gets deleted

---

### Expected Impact Metrics

| Metric | Current | After Phase 1 | After Phase 2 | After Phase 3 |
|--------|---------|---------------|---------------|---------------|
| Trial → Paid Conversion | 15% | **25%** (+10%) | **28%** (+3%) | **30%** (+2%) |
| Onboarding Completion | 85% | **90%** (+5%) | 90% | 90% |
| 3-Month Retention | 60% | 60% | **68%** (+8%) | **72%** (+4%) |
| Support Tickets/Month | 100 | **80** (-20%) | **60** (-20%) | 60 |

**Revenue Impact (1000 signups/month):**
- Current: 150 conversions × $6.99 = $1,048/month
- After improvements: 300 conversions × $6.99 = $2,097/month
- **Net gain: +$1,049/month (+100%)**

---

### Key UX Principles for Future Development

1. **Proactive Communication:** Warn users before limits, trial expiration, or changes
2. **Visibility:** Show usage stats, account status, and progress clearly
3. **Warmth:** Use friendly, conversational tone with appropriate emoji
4. **Flexibility:** Provide fallbacks (email links if SMS link fails)
5. **Data Safety:** Always preserve data, offer exports, soft deletes
6. **Feedback Loops:** Ask why users cancel, what features they want
7. **Progressive Enhancement:** Free tier should feel complete, not crippled
8. **Clear Value:** Remind users of benefits, especially before conversion points

---

### Quick Reference: Critical UX Files

| Journey Phase | Primary Files | Key Improvements Needed |
|---------------|---------------|------------------------|
| **Onboarding** | `services/onboarding_service.py` (121-391) | Welcome message, progress indicators |
| **Trial Management** | `tasks/reminder_tasks.py` | Expiration warnings (day 7, 13, 14) |
| **Premium Upgrade** | `main.py` (1774-1811), `services/stripe_service.py` | Value reminders, fallback options |
| **Usage Limits** | `services/tier_service.py` (225-331) | Proactive counters (X of Y) |
| **Account Status** | NEW: Create `routes/handlers/account.py` | INFO/STATUS command with stats |
| **Cancellation** | `services/stripe_service.py` (204-228) | Feedback collection, win-back |
