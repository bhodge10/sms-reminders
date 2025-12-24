"""
Formatting Utilities
Helper functions for formatting text and data
"""

def get_help_text():
    """Return help guide for users"""
    return """📖 How to Use This Service

💾 STORING MEMORIES:
Just text naturally!
• "My Honda Accord is a 2018, VIN ABC123"
• "Got new tires on March 15th"
• "Dentist is Dr. Smith, 555-1234"

🔍 FINDING MEMORIES:
Ask naturally:
• "What's my VIN?"
• "When did I get new tires?"
• "What's my dentist's number?"

⏰ SETTING REMINDERS:
• "Remind me at 9pm to take meds"
• "Remind me tomorrow at 2pm to call mom"
• "Remind me Saturday at 8am to mow lawn"
• "Remind me in 30 minutes to check laundry"

📋 COMMANDS:
• LIST ALL - View all your memories
• LIST REMINDERS - View all reminders
• DELETE ALL - Clear all your data (asks for confirmation)
• RESET ACCOUNT - Start over from scratch
• INFO (or ? or GUIDE) - Show this guide

💡 TIPS:
• For reminders, always include AM or PM
• I understand natural language - just talk normally!
• Your timezone is set from your ZIP code

Need more help? Just ask me a question!"""

def get_onboarding_prompt(step):
    """Get the appropriate prompt for the current onboarding step"""
    prompts = {
        1: "What's your first name?",
        2: "What's your last name?",
        3: "What's your email address?",
        4: "What's your ZIP code?"
    }
    return prompts.get(step, "Let's continue your setup!")
