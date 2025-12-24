# SMS Memory Service - Modular Architecture

## 📁 Project Structure

```
sms-service/
├── main.py                    # Entry point & FastAPI routes (288 lines)
├── config.py                  # Configuration & env variables (65 lines)
├── database.py                # Database initialization (79 lines)
├── requirements.txt           # Python dependencies
│
├── services/                  # Business logic layer
│   ├── __init__.py
│   ├── ai_service.py         # OpenAI processing (270 lines)
│   ├── sms_service.py        # Twilio SMS sending (18 lines)
│   ├── reminder_service.py   # Background reminder checking (40 lines)
│   └── onboarding_service.py # User onboarding flow (108 lines)
│
├── models/                    # Data access layer
│   ├── __init__.py
│   ├── user.py               # User database operations (67 lines)
│   ├── memory.py             # Memory database operations (36 lines)
│   └── reminder.py           # Reminder database operations (67 lines)
│
└── utils/                     # Helper functions
    ├── __init__.py
    ├── timezone.py           # Timezone utilities (31 lines)
    └── formatting.py         # Text formatting helpers (50 lines)
```

## 🎯 What Changed?

### Before:
- **1 file**: main.py (1,088 lines)
- Hard to navigate
- Difficult to test
- Scary to modify

### After:
- **14 files** organized by purpose
- Easy to find anything
- Testable modules
- Safe to modify

## 📚 File Responsibilities

### Core Files

**main.py**
- FastAPI application setup
- HTTP route definitions (`/sms`, `/health`, `/admin`)
- Webhook logic flow
- **What it does:** Routes requests to appropriate services

**config.py**
- Environment variable loading
- Application constants
- Logging configuration
- **What it does:** Centralized configuration management

**database.py**
- Database table initialization
- Connection management
- Interaction logging
- **What it does:** Database setup and utilities

### Services Layer (Business Logic)

**services/ai_service.py**
- OpenAI API integration
- Prompt construction
- Response parsing
- Memory/reminder context building
- **What it does:** All AI processing

**services/sms_service.py**
- Twilio client initialization
- SMS message sending
- **What it does:** All SMS operations

**services/reminder_service.py**
- Background reminder checking (runs every 60 seconds)
- Due reminder detection
- Reminder sending
- **What it does:** Automated reminder delivery

**services/onboarding_service.py**
- New user onboarding flow
- Step-by-step data collection
- Timezone setup
- **What it does:** User signup process

### Models Layer (Data Access)

**models/user.py**
- `get_user()` - Fetch user data
- `create_or_update_user()` - Save user data
- `is_user_onboarded()` - Check onboarding status
- `get_onboarding_step()` - Get current step
- `get_user_timezone()` - Get user's timezone
- **What it does:** All user database operations

**models/memory.py**
- `save_memory()` - Store new memory
- `get_memories()` - Retrieve memories
- **What it does:** All memory database operations

**models/reminder.py**
- `save_reminder()` - Store new reminder
- `get_due_reminders()` - Find reminders to send
- `mark_reminder_sent()` - Update sent status
- `get_user_reminders()` - Retrieve user's reminders
- **What it does:** All reminder database operations

### Utils Layer (Helpers)

**utils/timezone.py**
- `get_timezone_from_zip()` - ZIP → timezone conversion
- `get_user_current_time()` - Current time in user's timezone
- **What it does:** Timezone calculations

**utils/formatting.py**
- `get_help_text()` - Help guide text
- `get_onboarding_prompt()` - Onboarding step prompts
- **What it does:** User-facing text formatting

## 🔄 How It All Works Together

### Example: User Sends "Remind me at 9pm to take meds"

```
1. main.py receives SMS via /sms endpoint
2. main.py calls ai_service.process_with_ai()
3. ai_service.py:
   - Gets memories from models/memory.py
   - Gets reminders from models/reminder.py
   - Gets timezone from models/user.py
   - Calls OpenAI API
   - Returns action: "reminder"
4. main.py calls models/reminder.py save_reminder()
5. main.py calls services/sms_service.py send_sms() for confirmation
6. Background: services/reminder_service.py checks every 60 seconds
7. When time arrives: reminder_service sends SMS via sms_service
```

## 🚀 Benefits

### For Development
- **Find bugs faster** - Know exactly which file to check
- **Add features safely** - Changes isolated to one module
- **Test individually** - Each module can be tested separately
- **Onboard team members** - Clear structure, easy to understand

### For Scaling
- **Add new features** - Just create new service files
- **Swap implementations** - Want PostgreSQL? Just change database.py
- **Add team members** - Multiple people can work simultaneously
- **Deploy confidently** - Changes are contained and predictable

## 🛠️ How to Add New Features

### Example: Adding Billing

1. Create `services/billing_service.py`
```python
def create_subscription(phone_number, plan):
    # Stripe integration
    pass

def cancel_subscription(phone_number):
    pass
```

2. Create `models/subscription.py`
```python
def save_subscription(phone_number, stripe_id):
    # Save to database
    pass
```

3. Update `main.py` to add billing routes
```python
from services.billing_service import create_subscription

@app.post("/billing/subscribe")
async def subscribe(phone_number: str, plan: str):
    return create_subscription(phone_number, plan)
```

That's it! No touching existing reminder or memory code.

## 📝 Development Workflow

### Making Changes

1. **Identify the module** to change
   - AI prompts? → `services/ai_service.py`
   - Database schema? → `database.py`
   - User onboarding? → `services/onboarding_service.py`

2. **Make the change** in that one file

3. **Test** the specific module

4. **Deploy** with confidence

### Adding Features

1. **Create new service** in `services/`
2. **Create new model** in `models/` (if needed)
3. **Import in main.py**
4. **Add routes** in main.py

## 🧪 Testing Strategy (Future)

```
tests/
├── test_ai_service.py       # Test AI processing
├── test_reminders.py        # Test reminder logic
├── test_onboarding.py       # Test onboarding flow
└── test_timezone.py         # Test timezone conversions
```

Each module can be tested independently!

## 📊 Code Statistics

| Module | Lines | Complexity |
|--------|-------|------------|
| ai_service.py | 270 | High |
| main.py | 288 | Medium |
| onboarding_service.py | 108 | Medium |
| database.py | 79 | Low |
| user.py | 67 | Low |
| reminder.py | 67 | Low |
| config.py | 65 | Low |
| formatting.py | 50 | Low |
| reminder_service.py | 40 | Low |
| memory.py | 36 | Low |
| timezone.py | 31 | Low |
| sms_service.py | 18 | Low |

**Total: ~1,119 lines** (similar to before, but organized!)

## 🎓 Learning Resources

- **New to modular architecture?** Start with `main.py` to see the flow
- **Want to understand AI?** Read `services/ai_service.py`
- **Working on database?** Check `models/` folder
- **Adding features?** Follow the "How to Add New Features" guide

## ⚠️ Important Notes

1. **Don't edit main.py directly in production** - test in dev first
2. **Database.py changes require migration** - be careful!
3. **Config.py changes need redeployment** - environment variables
4. **Service files are independent** - safe to modify

## 🚀 Deployment

Same as before! The modular structure is transparent to deployment:

```bash
# All files are in the same directory
# Just run main.py as usual
python main.py
```

Or in Replit, just click "Run" - it works the same!

## 💡 Pro Tips

1. **Read main.py first** - It's the roadmap
2. **Follow the imports** - They show dependencies
3. **One change, one file** - Keep changes focused
4. **Test in dev** - Use your dev/prod split
5. **Add docstrings** - Explain complex functions

## 📧 Questions?

This structure follows industry best practices for Python applications. Each module has a single responsibility, making the codebase:
- **Maintainable** ✅
- **Testable** ✅
- **Scalable** ✅
- **Team-friendly** ✅

Happy coding! 🎉
