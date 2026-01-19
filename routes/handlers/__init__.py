"""
Route Handlers Package
Modular handlers for SMS message processing states and AI actions
"""

# Pending state handlers (confirmation flows)
from routes.handlers.pending_states import (
    handle_pending_delete,
    handle_pending_memory_delete,
    handle_pending_reminder_date,
    handle_pending_list_create,
    handle_pending_list_item,
    handle_pending_reminder_confirmation,
    handle_time_clarification,
)

# Reminder action handlers
from routes.handlers.reminders import (
    handle_list_reminders,
    handle_clarify_time,
    handle_clarify_date_time,
    handle_clarify_specific_time,
    handle_reminder,
    handle_reminder_relative,
    handle_delete_reminder,
    format_reminder_confirmation,
    format_reminders_list,
)

# List action handlers
from routes.handlers.lists import (
    handle_create_list,
    handle_add_to_list,
    handle_add_item_ask_list,
    handle_show_list,
    handle_show_current_list,
    handle_show_all_lists,
    handle_complete_item,
    handle_uncomplete_item,
    handle_delete_item,
    handle_delete_list,
    handle_clear_list,
    handle_rename_list,
)

# Memory action handlers
from routes.handlers.memories import (
    handle_store_memory,
    handle_retrieve_memory,
    handle_delete_memory,
)

__all__ = [
    # Pending states
    'handle_pending_delete',
    'handle_pending_memory_delete',
    'handle_pending_reminder_date',
    'handle_pending_list_create',
    'handle_pending_list_item',
    'handle_pending_reminder_confirmation',
    'handle_time_clarification',
    # Reminders
    'handle_list_reminders',
    'handle_clarify_time',
    'handle_clarify_date_time',
    'handle_clarify_specific_time',
    'handle_reminder',
    'handle_reminder_relative',
    'handle_delete_reminder',
    'format_reminder_confirmation',
    'format_reminders_list',
    # Lists
    'handle_create_list',
    'handle_add_to_list',
    'handle_add_item_ask_list',
    'handle_show_list',
    'handle_show_current_list',
    'handle_show_all_lists',
    'handle_complete_item',
    'handle_uncomplete_item',
    'handle_delete_item',
    'handle_delete_list',
    'handle_clear_list',
    'handle_rename_list',
    # Memories
    'handle_store_memory',
    'handle_retrieve_memory',
    'handle_delete_memory',
]
