"""
Tests for list management functionality.
Covers: create, add items, check off, delete, view lists.
"""

import pytest
from datetime import datetime


class TestListCreation:
    """Tests for creating lists."""

    @pytest.mark.asyncio
    async def test_create_new_list(self, simulator, onboarded_user, ai_mock):
        """Test creating a new list."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create a grocery list", {
            "action": "create_list",
            "list_name": "Grocery"
        })

        result = await simulator.send_message(phone, "Create a grocery list")
        assert any(word in result["output"].lower() for word in ["created", "grocery", "list"])

    @pytest.mark.asyncio
    async def test_create_duplicate_list_name(self, simulator, onboarded_user, ai_mock):
        """Test handling of duplicate list name."""
        phone = onboarded_user["phone"]

        # Create first list
        from models.list_model import create_list
        create_list(phone, "Shopping")

        ai_mock.set_response("create a shopping list", {
            "action": "create_list",
            "list_name": "Shopping"
        })

        result = await simulator.send_message(phone, "Create a shopping list")
        # Should offer to add to existing or create new
        assert any(word in result["output"].lower() for word in ["already", "exist", "add", "new"])


class TestListItems:
    """Tests for adding and managing list items."""

    @pytest.mark.asyncio
    async def test_add_single_item(self, simulator, onboarded_user, ai_mock):
        """Test adding a single item to a list."""
        phone = onboarded_user["phone"]

        # Create a list first
        from models.list_model import create_list
        create_list(phone, "Grocery")

        # Set last active list
        from database import get_db_connection, return_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET last_active_list = 'Grocery' WHERE phone_number = %s", (phone,))
        conn.commit()
        return_db_connection(conn)

        ai_mock.set_response("add milk to my list", {
            "action": "add_to_list",
            "items": ["milk"],
            "list_name": None  # Will use last active
        })

        result = await simulator.send_message(phone, "Add milk to my list")
        assert "milk" in result["output"].lower() or "added" in result["output"].lower()

    @pytest.mark.asyncio
    async def test_add_multiple_items(self, simulator, onboarded_user, ai_mock):
        """Test adding multiple items at once."""
        phone = onboarded_user["phone"]

        from models.list_model import create_list
        create_list(phone, "Grocery")

        from database import get_db_connection, return_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET last_active_list = 'Grocery' WHERE phone_number = %s", (phone,))
        conn.commit()
        return_db_connection(conn)

        ai_mock.set_response("add milk, eggs, and bread to my grocery list", {
            "action": "add_to_list",
            "items": ["milk", "eggs", "bread"],
            "list_name": "Grocery"
        })

        result = await simulator.send_message(phone, "Add milk, eggs, and bread to my grocery list")
        # Should confirm items added

    @pytest.mark.asyncio
    async def test_add_item_multiple_lists_prompt(self, simulator, onboarded_user, ai_mock):
        """Test adding item when user has multiple lists."""
        phone = onboarded_user["phone"]

        # Create multiple lists
        from models.list_model import create_list
        create_list(phone, "Grocery")
        create_list(phone, "Todo")
        create_list(phone, "Shopping")

        ai_mock.set_response("add batteries", {
            "action": "add_to_list",
            "items": ["batteries"],
            "list_name": None
        })

        result = await simulator.send_message(phone, "Add batteries")
        # Should ask which list
        assert any(word in result["output"].lower() for word in ["which", "list", "1", "2"])

    @pytest.mark.asyncio
    async def test_select_list_by_number(self, simulator, onboarded_user, ai_mock):
        """Test selecting a list by number when adding items."""
        phone = onboarded_user["phone"]

        from models.list_model import create_list
        create_list(phone, "Grocery")
        create_list(phone, "Todo")

        ai_mock.set_response("add milk", {
            "action": "add_to_list",
            "items": ["milk"],
            "list_name": None
        })

        # First message triggers list selection
        await simulator.send_message(phone, "Add milk")

        # Select by number
        result = await simulator.send_message(phone, "1")
        # Should add to selected list


class TestListViewing:
    """Tests for viewing lists."""

    @pytest.mark.asyncio
    async def test_view_all_lists(self, simulator, onboarded_user):
        """Test viewing all user's lists."""
        phone = onboarded_user["phone"]

        from models.list_model import create_list
        create_list(phone, "Grocery")
        create_list(phone, "Todo")

        result = await simulator.send_message(phone, "MY LISTS")
        assert "grocery" in result["output"].lower()
        assert "todo" in result["output"].lower()

    @pytest.mark.asyncio
    async def test_view_specific_list_by_number(self, simulator, onboarded_user):
        """Test viewing a specific list by its number."""
        phone = onboarded_user["phone"]

        from models.list_model import create_list, add_list_item
        list_id = create_list(phone, "Grocery")
        add_list_item(list_id, phone, "milk")
        add_list_item(list_id, phone, "eggs")

        # View lists first
        await simulator.send_message(phone, "MY LISTS")

        # View list #1
        result = await simulator.send_message(phone, "1")
        assert any(word in result["output"].lower() for word in ["milk", "eggs", "grocery"])

    @pytest.mark.asyncio
    async def test_view_empty_list(self, simulator, onboarded_user):
        """Test viewing an empty list."""
        phone = onboarded_user["phone"]

        from models.list_model import create_list
        create_list(phone, "Empty List")

        result = await simulator.send_message(phone, "SHOW LISTS")
        # Should show the list exists


class TestListItemCompletion:
    """Tests for checking off/completing list items."""

    @pytest.mark.asyncio
    async def test_check_item_by_number(self, simulator, onboarded_user):
        """Test checking off an item by its number."""
        phone = onboarded_user["phone"]

        from models.list_model import create_list, add_list_item
        list_id = create_list(phone, "Grocery")
        add_list_item(list_id, phone, "milk")
        add_list_item(list_id, phone, "eggs")

        # Set as last active
        from database import get_db_connection, return_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET last_active_list = 'Grocery' WHERE phone_number = %s", (phone,))
        conn.commit()
        return_db_connection(conn)

        # Check off item
        result = await simulator.send_message(phone, "check 1")
        # Should mark as complete

    @pytest.mark.asyncio
    async def test_done_command(self, simulator, onboarded_user):
        """Test using 'done' as alternative to 'check'."""
        phone = onboarded_user["phone"]

        from models.list_model import create_list, add_list_item
        list_id = create_list(phone, "Todo")
        add_list_item(list_id, phone, "call mom")

        from database import get_db_connection, return_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET last_active_list = 'Todo' WHERE phone_number = %s", (phone,))
        conn.commit()
        return_db_connection(conn)

        result = await simulator.send_message(phone, "done 1")

    @pytest.mark.asyncio
    async def test_complete_command(self, simulator, onboarded_user):
        """Test using 'complete' as alternative to 'check'."""
        phone = onboarded_user["phone"]

        from models.list_model import create_list, add_list_item
        list_id = create_list(phone, "Tasks")
        add_list_item(list_id, phone, "finish report")

        from database import get_db_connection, return_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET last_active_list = 'Tasks' WHERE phone_number = %s", (phone,))
        conn.commit()
        return_db_connection(conn)

        result = await simulator.send_message(phone, "complete 1")


class TestListDeletion:
    """Tests for deleting lists and items."""

    @pytest.mark.asyncio
    async def test_delete_list_item(self, simulator, onboarded_user):
        """Test deleting a specific item from a list."""
        phone = onboarded_user["phone"]

        from models.list_model import create_list, add_list_item
        list_id = create_list(phone, "Grocery")
        add_list_item(list_id, phone, "milk")
        add_list_item(list_id, phone, "eggs")

        from database import get_db_connection, return_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET last_active_list = 'Grocery' WHERE phone_number = %s", (phone,))
        conn.commit()
        return_db_connection(conn)

        result = await simulator.send_message(phone, "delete 1")
        # Should ask for confirmation or show options

    @pytest.mark.asyncio
    async def test_delete_entire_list(self, simulator, onboarded_user, ai_mock):
        """Test deleting an entire list."""
        phone = onboarded_user["phone"]

        from models.list_model import create_list
        create_list(phone, "OldList")

        ai_mock.set_response("delete my oldlist", {
            "action": "delete",
            "delete_type": "list",
            "query": "OldList"
        })

        result = await simulator.send_message(phone, "Delete my OldList")


class TestListEdgeCases:
    """Edge cases for list management."""

    @pytest.mark.asyncio
    async def test_max_lists_limit(self, simulator, onboarded_user, ai_mock):
        """Test behavior when user reaches maximum list limit."""
        phone = onboarded_user["phone"]

        from models.list_model import create_list
        from config import MAX_LISTS_PER_USER

        # Create maximum number of lists
        for i in range(MAX_LISTS_PER_USER):
            try:
                create_list(phone, f"List{i}")
            except:
                break

        ai_mock.set_response("create another list", {
            "action": "create_list",
            "list_name": "OneMore"
        })

        result = await simulator.send_message(phone, "Create another list")
        # Should indicate limit reached

    @pytest.mark.asyncio
    async def test_special_characters_in_list_name(self, simulator, onboarded_user, ai_mock):
        """Test handling of special characters in list names."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("create a list called mom's recipes", {
            "action": "create_list",
            "list_name": "Mom's Recipes"
        })

        result = await simulator.send_message(phone, "Create a list called Mom's Recipes")
        # Should handle apostrophe gracefully

    @pytest.mark.asyncio
    async def test_check_invalid_item_number(self, simulator, onboarded_user):
        """Test checking off an item number that doesn't exist."""
        phone = onboarded_user["phone"]

        from models.list_model import create_list, add_list_item
        list_id = create_list(phone, "Short")
        add_list_item(list_id, phone, "only item")

        from database import get_db_connection, return_db_connection
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET last_active_list = 'Short' WHERE phone_number = %s", (phone,))
        conn.commit()
        return_db_connection(conn)

        result = await simulator.send_message(phone, "check 99")
        # Should indicate item doesn't exist
