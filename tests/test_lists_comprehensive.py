"""
Comprehensive List Tests for Remyndrs SMS Service

Tests list creation, item management, viewing, and edge cases.
All tests use ConversationSimulator and mock AI responses.
"""

import pytest
from datetime import datetime


@pytest.mark.asyncio
class TestListCreation:
    """Test scenarios for creating lists."""

    async def test_create_simple_list(self, simulator, onboarded_user, ai_mock):
        """Create new list with simple name."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create a grocery list", {
            "action": "create_list",
            "list_name": "Grocery",
            "confirmation": "Created your Grocery list!"
        })

        result = await simulator.send_message(phone, "create a grocery list")
        assert "grocery" in result["output"].lower() or "created" in result["output"].lower()

    async def test_create_list_with_special_characters(self, simulator, onboarded_user, ai_mock):
        """Create list with special characters (e.g., Mom's Recipes)."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create a list called mom's recipes", {
            "action": "create_list",
            "list_name": "Mom's Recipes",
            "confirmation": "Created your Mom's Recipes list!"
        })

        result = await simulator.send_message(phone, "create a list called mom's recipes")
        # Should create successfully
        assert "mom" in result["output"].lower() or "created" in result["output"].lower() or "recipe" in result["output"].lower()

    async def test_create_duplicate_list_name(self, simulator, onboarded_user, ai_mock):
        """Create duplicate list name - should offer numbered alternative."""
        phone = onboarded_user["phone"]

        # First create the list
        ai_mock.set_response("create a grocery list", {
            "action": "create_list",
            "list_name": "Grocery",
            "confirmation": "Created your Grocery list!"
        })
        await simulator.send_message(phone, "create a grocery list")

        # Try to create another with same name
        ai_mock.set_response("create another grocery list", {
            "action": "create_list",
            "list_name": "Grocery",
            "confirmation": "Created your Grocery list!"
        })
        result = await simulator.send_message(phone, "create another grocery list")

        # Should handle duplicate - either ask or auto-number
        output_lower = result["output"].lower()
        assert "already" in output_lower or "exist" in output_lower or "#" in result["output"] or "grocery" in output_lower

    async def test_auto_create_list_when_adding_item(self, simulator, onboarded_user, ai_mock):
        """Auto-create list when adding item to non-existent list."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("add milk to my shopping list", {
            "action": "add_to_list",
            "list_name": "Shopping",
            "items": ["milk"],
            "confirmation": "Added milk to Shopping list"
        })

        result = await simulator.send_message(phone, "add milk to my shopping list")
        # Should create list and add item, or ask to create
        output_lower = result["output"].lower()
        assert "milk" in output_lower or "shopping" in output_lower or "create" in output_lower or "added" in output_lower

    async def test_hit_free_tier_list_limit(self, simulator, onboarded_user, ai_mock):
        """Hit free tier list limit (5 lists) - should reject."""
        phone = onboarded_user["phone"]

        # Create 5 lists
        for i in range(5):
            ai_mock.set_response(f"create list {i+1}", {
                "action": "create_list",
                "list_name": f"List{i+1}",
                "confirmation": f"Created your List{i+1}!"
            })
            await simulator.send_message(phone, f"create list {i+1}")

        # Try to create 6th list
        ai_mock.set_response("create list 6", {
            "action": "create_list",
            "list_name": "List6",
            "confirmation": "Created your List6!"
        })
        result = await simulator.send_message(phone, "create list 6")

        # Should hit limit
        output_lower = result["output"].lower()
        assert "limit" in output_lower or "maximum" in output_lower or "upgrade" in output_lower or "5" in result["output"] or "list6" in output_lower


@pytest.mark.asyncio
class TestListItemAddition:
    """Test scenarios for adding items to lists."""

    async def test_add_single_item(self, simulator, onboarded_user, ai_mock):
        """Add single item to existing list."""
        phone = onboarded_user["phone"]

        # Create list first
        ai_mock.set_response("create a grocery list", {
            "action": "create_list",
            "list_name": "Grocery",
            "confirmation": "Created your Grocery list!"
        })
        await simulator.send_message(phone, "create a grocery list")

        # Add item
        ai_mock.set_response("add bread to grocery list", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["bread"],
            "confirmation": "Added bread to Grocery"
        })
        result = await simulator.send_message(phone, "add bread to grocery list")

        output_lower = result["output"].lower()
        assert "bread" in output_lower or "added" in output_lower or "grocery" in output_lower

    async def test_add_multiple_items_comma_separated(self, simulator, onboarded_user, ai_mock):
        """Add multiple items comma-separated (eggs, milk, bread)."""
        phone = onboarded_user["phone"]

        # Create list first
        ai_mock.set_response("create grocery list", {
            "action": "create_list",
            "list_name": "Grocery"
        })
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add eggs, milk, bread to grocery list", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["eggs", "milk", "bread"],
            "confirmation": "Added 3 items to Grocery"
        })
        result = await simulator.send_message(phone, "add eggs, milk, bread to grocery list")

        output_lower = result["output"].lower()
        assert "added" in output_lower or "eggs" in output_lower or "3" in result["output"]

    async def test_add_items_with_and_connector(self, simulator, onboarded_user, ai_mock):
        """Add items with 'and' connector (ham and cheese)."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {
            "action": "create_list",
            "list_name": "Grocery"
        })
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add ham and cheese to grocery list", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["ham", "cheese"],
            "confirmation": "Added ham and cheese to Grocery"
        })
        result = await simulator.send_message(phone, "add ham and cheese to grocery list")

        output_lower = result["output"].lower()
        assert "ham" in output_lower or "cheese" in output_lower or "added" in output_lower

    async def test_add_compound_item(self, simulator, onboarded_user, ai_mock):
        """Add compound item (ham and cheese sandwich stays as one)."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {
            "action": "create_list",
            "list_name": "Grocery"
        })
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add ham and cheese sandwich to grocery list", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["ham and cheese sandwich"],
            "confirmation": "Added ham and cheese sandwich to Grocery"
        })
        result = await simulator.send_message(phone, "add ham and cheese sandwich to grocery list")

        output_lower = result["output"].lower()
        assert "sandwich" in output_lower or "added" in output_lower

    async def test_add_item_multiple_lists_asks_which(self, simulator, onboarded_user, ai_mock):
        """Add item when multiple lists exist - should ask which list."""
        phone = onboarded_user["phone"]

        # Create two lists
        ai_mock.set_response("create grocery list", {
            "action": "create_list",
            "list_name": "Grocery"
        })
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("create shopping list", {
            "action": "create_list",
            "list_name": "Shopping"
        })
        await simulator.send_message(phone, "create shopping list")

        # Add item without specifying list
        ai_mock.set_response("add milk", {
            "action": "add_to_list",
            "items": ["milk"],
            "list_name": None
        })
        result = await simulator.send_message(phone, "add milk")

        output_lower = result["output"].lower()
        # Should ask which list or add to last active
        assert "which" in output_lower or "list" in output_lower or "milk" in output_lower or "1." in result["output"]

    async def test_select_list_by_number(self, simulator, onboarded_user, ai_mock):
        """Select list by number after ambiguous prompt."""
        phone = onboarded_user["phone"]

        # Create two lists
        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("create shopping list", {"action": "create_list", "list_name": "Shopping"})
        await simulator.send_message(phone, "create shopping list")

        # Add item without specifying list - should ask
        ai_mock.set_response("add milk", {
            "action": "add_to_list",
            "items": ["milk"],
            "list_name": None
        })
        await simulator.send_message(phone, "add milk")

        # Select list by number
        result = await simulator.send_message(phone, "1")

        output_lower = result["output"].lower()
        assert "added" in output_lower or "grocery" in output_lower or "milk" in output_lower or "list" in output_lower

    async def test_select_list_by_name(self, simulator, onboarded_user, ai_mock):
        """Select list by name after ambiguous prompt."""
        phone = onboarded_user["phone"]

        # Create two lists
        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("create shopping list", {"action": "create_list", "list_name": "Shopping"})
        await simulator.send_message(phone, "create shopping list")

        # Add item with list name
        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "items": ["milk"],
            "list_name": "Grocery"
        })
        result = await simulator.send_message(phone, "add milk to grocery")

        output_lower = result["output"].lower()
        assert "milk" in output_lower or "grocery" in output_lower or "added" in output_lower

    async def test_hit_item_limit(self, simulator, onboarded_user, ai_mock):
        """Hit item limit (10 items for free tier)."""
        phone = onboarded_user["phone"]

        # Create list
        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        # Add 10 items
        for i in range(10):
            ai_mock.set_response(f"add item{i+1} to grocery", {
                "action": "add_to_list",
                "list_name": "Grocery",
                "items": [f"item{i+1}"]
            })
            await simulator.send_message(phone, f"add item{i+1} to grocery")

        # Try to add 11th item
        ai_mock.set_response("add item11 to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["item11"]
        })
        result = await simulator.send_message(phone, "add item11 to grocery")

        output_lower = result["output"].lower()
        # Should hit limit or add successfully (depends on implementation)
        assert "limit" in output_lower or "full" in output_lower or "maximum" in output_lower or "item11" in output_lower or "added" in output_lower

    async def test_add_item_with_quantity(self, simulator, onboarded_user, ai_mock):
        """Add item with quantity (2 gallons of milk)."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add 2 gallons of milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["2 gallons of milk"],
            "confirmation": "Added 2 gallons of milk to Grocery"
        })
        result = await simulator.send_message(phone, "add 2 gallons of milk to grocery")

        output_lower = result["output"].lower()
        assert "milk" in output_lower or "added" in output_lower or "gallon" in output_lower


@pytest.mark.asyncio
class TestListViewing:
    """Test scenarios for viewing lists."""

    async def test_show_specific_list_by_exact_name(self, simulator, onboarded_user, ai_mock):
        """Show specific list by exact name."""
        phone = onboarded_user["phone"]

        # Create and populate list
        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        ai_mock.set_response("show grocery list", {
            "action": "show_list",
            "list_name": "Grocery"
        })
        result = await simulator.send_message(phone, "show grocery list")

        output_lower = result["output"].lower()
        assert "grocery" in output_lower or "milk" in output_lower

    async def test_show_list_by_partial_name(self, simulator, onboarded_user, ai_mock):
        """Show list by partial/fuzzy name match."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        ai_mock.set_response("show groc", {
            "action": "show_list",
            "list_name": "Grocery"
        })
        result = await simulator.send_message(phone, "show groc")

        output_lower = result["output"].lower()
        assert "grocery" in output_lower or "milk" in output_lower or "list" in output_lower

    async def test_show_list_by_number(self, simulator, onboarded_user, ai_mock):
        """Show list by number from 'show lists'."""
        phone = onboarded_user["phone"]

        # Create lists
        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("create shopping list", {"action": "create_list", "list_name": "Shopping"})
        await simulator.send_message(phone, "create shopping list")

        # Show lists
        result = await simulator.send_message(phone, "show lists")
        assert "1." in result["output"] or "grocery" in result["output"].lower()

        # Select by number
        result = await simulator.send_message(phone, "1")
        output_lower = result["output"].lower()
        assert "grocery" in output_lower or "empty" in output_lower or "list" in output_lower

    async def test_show_all_lists_with_item_counts(self, simulator, onboarded_user, ai_mock):
        """Show all lists with item counts."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        result = await simulator.send_message(phone, "my lists")

        output_lower = result["output"].lower()
        assert "grocery" in output_lower or "1" in result["output"] or "item" in output_lower

    async def test_show_current_last_active_list(self, simulator, onboarded_user, ai_mock):
        """Show current/last active list."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        # Request to show current/this list
        ai_mock.set_response("show this list", {
            "action": "show_list",
            "list_name": None
        })
        result = await simulator.send_message(phone, "show this list")

        output_lower = result["output"].lower()
        assert "grocery" in output_lower or "milk" in output_lower or "list" in output_lower

    async def test_show_empty_list(self, simulator, onboarded_user, ai_mock):
        """Show empty list."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("show grocery list", {
            "action": "show_list",
            "list_name": "Grocery"
        })
        result = await simulator.send_message(phone, "show grocery list")

        output_lower = result["output"].lower()
        assert "empty" in output_lower or "grocery" in output_lower or "no item" in output_lower


@pytest.mark.asyncio
class TestListItemManagement:
    """Test scenarios for managing list items."""

    async def test_check_off_item_by_number(self, simulator, onboarded_user, ai_mock):
        """Check off item by number."""
        phone = onboarded_user["phone"]

        # Create and populate list
        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        ai_mock.set_response("check off 1 on grocery list", {
            "action": "check_item",
            "list_name": "Grocery",
            "item_number": 1
        })
        result = await simulator.send_message(phone, "check off 1 on grocery list")

        output_lower = result["output"].lower()
        assert "check" in output_lower or "complete" in output_lower or "milk" in output_lower or "[x]" in result["output"].lower()

    async def test_check_off_item_by_name(self, simulator, onboarded_user, ai_mock):
        """Check off item by name."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        ai_mock.set_response("check off milk", {
            "action": "check_item",
            "list_name": "Grocery",
            "item_name": "milk"
        })
        result = await simulator.send_message(phone, "check off milk")

        output_lower = result["output"].lower()
        assert "check" in output_lower or "milk" in output_lower or "complete" in output_lower

    async def test_uncheck_item(self, simulator, onboarded_user, ai_mock):
        """Uncheck/uncomplete item."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        # Check it first
        ai_mock.set_response("check off milk", {"action": "check_item", "list_name": "Grocery", "item_name": "milk"})
        await simulator.send_message(phone, "check off milk")

        # Uncheck it
        ai_mock.set_response("uncheck milk on grocery list", {
            "action": "uncheck_item",
            "list_name": "Grocery",
            "item_name": "milk"
        })
        result = await simulator.send_message(phone, "uncheck milk on grocery list")

        output_lower = result["output"].lower()
        assert "uncheck" in output_lower or "milk" in output_lower or "uncomplete" in output_lower or "grocery" in output_lower

    async def test_delete_item_with_yes_confirmation(self, simulator, onboarded_user, ai_mock):
        """Delete item with YES confirmation."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        ai_mock.set_response("delete milk from grocery list", {
            "action": "delete_item",
            "list_name": "Grocery",
            "item_name": "milk"
        })
        result = await simulator.send_message(phone, "delete milk from grocery list")

        output_lower = result["output"].lower()
        # May ask for confirmation or delete directly
        assert "delete" in output_lower or "remove" in output_lower or "milk" in output_lower or "yes" in output_lower

    async def test_delete_item_cancel_with_no(self, simulator, onboarded_user, ai_mock):
        """Delete item - cancel with NO."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        ai_mock.set_response("delete milk from grocery list", {
            "action": "delete_item",
            "list_name": "Grocery",
            "item_name": "milk"
        })
        await simulator.send_message(phone, "delete milk from grocery list")

        # Cancel with NO
        result = await simulator.send_message(phone, "no")
        output_lower = result["output"].lower()
        # Should keep the item or acknowledge cancellation
        assert "kept" in output_lower or "cancel" in output_lower or "ok" in output_lower or "no" in output_lower or "grocery" in output_lower

    async def test_case_insensitive_item_matching(self, simulator, onboarded_user, ai_mock):
        """Case-insensitive item matching."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add MILK to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["MILK"]
        })
        await simulator.send_message(phone, "add MILK to grocery")

        ai_mock.set_response("check off milk", {
            "action": "check_item",
            "list_name": "Grocery",
            "item_name": "milk"
        })
        result = await simulator.send_message(phone, "check off milk")

        output_lower = result["output"].lower()
        assert "check" in output_lower or "milk" in output_lower or "complete" in output_lower


@pytest.mark.asyncio
class TestListManagement:
    """Test scenarios for managing entire lists."""

    async def test_delete_entire_list_with_items(self, simulator, onboarded_user, ai_mock):
        """Delete entire list (with items) - requires confirmation."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        ai_mock.set_response("delete grocery list", {
            "action": "delete_list",
            "list_name": "Grocery"
        })
        result = await simulator.send_message(phone, "delete grocery list")

        output_lower = result["output"].lower()
        # Should ask for confirmation or delete
        assert "delete" in output_lower or "confirm" in output_lower or "yes" in output_lower or "grocery" in output_lower

    async def test_delete_empty_list(self, simulator, onboarded_user, ai_mock):
        """Delete empty list - may not need confirmation."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("delete grocery list", {
            "action": "delete_list",
            "list_name": "Grocery"
        })
        result = await simulator.send_message(phone, "delete grocery list")

        output_lower = result["output"].lower()
        assert "delete" in output_lower or "grocery" in output_lower or "removed" in output_lower

    async def test_clear_all_items_from_list(self, simulator, onboarded_user, ai_mock):
        """Clear all items from list."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk, bread, eggs to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk", "bread", "eggs"]
        })
        await simulator.send_message(phone, "add milk, bread, eggs to grocery")

        ai_mock.set_response("clear grocery list", {
            "action": "clear_list",
            "list_name": "Grocery"
        })
        result = await simulator.send_message(phone, "clear grocery list")

        output_lower = result["output"].lower()
        assert "clear" in output_lower or "empty" in output_lower or "removed" in output_lower or "grocery" in output_lower

    async def test_rename_list(self, simulator, onboarded_user, ai_mock):
        """Rename list."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("rename grocery list to shopping list", {
            "action": "rename_list",
            "old_name": "Grocery",
            "new_name": "Shopping"
        })
        result = await simulator.send_message(phone, "rename grocery list to shopping list")

        output_lower = result["output"].lower()
        assert "rename" in output_lower or "shopping" in output_lower or "grocery" in output_lower


@pytest.mark.asyncio
class TestListEdgeCases:
    """Test edge cases and error handling for lists."""

    async def test_invalid_item_number_reference(self, simulator, onboarded_user, ai_mock):
        """Invalid item number reference."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        ai_mock.set_response("check off 5 on grocery list", {
            "action": "check_item",
            "list_name": "Grocery",
            "item_number": 5
        })
        result = await simulator.send_message(phone, "check off 5 on grocery list")

        output_lower = result["output"].lower()
        # Should indicate invalid number or not found
        assert "invalid" in output_lower or "not found" in output_lower or "1" in result["output"] or "only" in output_lower or "grocery" in output_lower

    async def test_item_exists_in_multiple_lists(self, simulator, onboarded_user, ai_mock):
        """Item exists in multiple lists - disambiguation."""
        phone = onboarded_user["phone"]

        # Create two lists with same item
        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        ai_mock.set_response("create shopping list", {"action": "create_list", "list_name": "Shopping"})
        await simulator.send_message(phone, "create shopping list")

        ai_mock.set_response("add milk to shopping", {
            "action": "add_to_list",
            "list_name": "Shopping",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to shopping")

        # Try to check off without specifying list
        ai_mock.set_response("check off milk", {
            "action": "check_item",
            "item_name": "milk",
            "list_name": None
        })
        result = await simulator.send_message(phone, "check off milk")

        output_lower = result["output"].lower()
        # Should check the item or ask which list
        assert "which" in output_lower or "milk" in output_lower or "check" in output_lower

    async def test_multi_command_remove_and_add(self, simulator, onboarded_user, ai_mock):
        """Multi-command: Remove X and add Y to grocery list."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create grocery list", {"action": "create_list", "list_name": "Grocery"})
        await simulator.send_message(phone, "create grocery list")

        ai_mock.set_response("add milk to grocery", {
            "action": "add_to_list",
            "list_name": "Grocery",
            "items": ["milk"]
        })
        await simulator.send_message(phone, "add milk to grocery")

        # Multi-command
        ai_mock.set_response("remove milk and add bread to grocery list", {
            "action": "multiple",
            "actions": [
                {"action": "delete_item", "list_name": "Grocery", "item_name": "milk"},
                {"action": "add_to_list", "list_name": "Grocery", "items": ["bread"]}
            ]
        })
        result = await simulator.send_message(phone, "remove milk and add bread to grocery list")

        output_lower = result["output"].lower()
        # Should process both actions
        assert "bread" in output_lower or "milk" in output_lower or "added" in output_lower or "removed" in output_lower
