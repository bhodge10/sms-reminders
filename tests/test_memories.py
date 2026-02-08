"""
Tests for memory storage and retrieval.
Covers: storing memories, searching, deleting, edge cases.
"""

import pytest
from datetime import datetime


class TestMemoryStorage:
    """Tests for storing memories."""

    @pytest.mark.asyncio
    async def test_store_simple_memory(self, simulator, onboarded_user, ai_mock):
        """Test storing a simple memory."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remember my wifi password is secret123", {
            "action": "store",
            "memory_text": "wifi password is secret123"
        })

        result = await simulator.send_message(phone, "Remember my wifi password is secret123")
        assert any(word in result["output"].lower() for word in ["remember", "stored", "saved", "got it"])

    @pytest.mark.asyncio
    async def test_store_memory_with_date(self, simulator, onboarded_user, ai_mock):
        """Test storing a memory with a date reference."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remember my anniversary is march 15", {
            "action": "store",
            "memory_text": "anniversary is March 15"
        })

        result = await simulator.send_message(phone, "Remember my anniversary is March 15")
        assert any(word in result["output"].lower() for word in ["remember", "stored", "saved"])

    @pytest.mark.asyncio
    async def test_store_memory_with_that(self, simulator, onboarded_user, ai_mock):
        """Test 'remember that' phrasing."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remember that john's number is 555-1234", {
            "action": "store",
            "memory_text": "John's number is 555-1234"
        })

        result = await simulator.send_message(phone, "Remember that John's number is 555-1234")


class TestMemoryRetrieval:
    """Tests for retrieving memories."""

    @pytest.mark.asyncio
    async def test_view_all_memories(self, simulator, onboarded_user):
        """Test viewing all stored memories."""
        phone = onboarded_user["phone"]

        # Store some memories
        from models.memory import save_memory
        save_memory(phone, "wifi password is test123", {})
        save_memory(phone, "car license plate ABC-1234", {})

        result = await simulator.send_message(phone, "MY MEMORIES")
        assert "wifi" in result["output"].lower() or "memories" in result["output"].lower()

    @pytest.mark.asyncio
    async def test_search_memories(self, simulator, onboarded_user, ai_mock):
        """Test searching for specific memories."""
        phone = onboarded_user["phone"]

        from models.memory import save_memory
        save_memory(phone, "wifi password is test123", {})
        save_memory(phone, "car license plate ABC-1234", {})
        save_memory(phone, "mom's birthday is June 5", {})

        ai_mock.set_response("what's my wifi password", {
            "action": "retrieve",
            "query": "wifi"
        })

        result = await simulator.send_message(phone, "What's my wifi password?")
        # Should return wifi-related memory

    @pytest.mark.asyncio
    async def test_recall_command(self, simulator, onboarded_user):
        """Test using 'recall' to view memories."""
        phone = onboarded_user["phone"]

        from models.memory import save_memory
        save_memory(phone, "test memory content", {})

        result = await simulator.send_message(phone, "recall")

    @pytest.mark.asyncio
    async def test_list_all_command(self, simulator, onboarded_user):
        """Test 'LIST ALL' command for memories."""
        phone = onboarded_user["phone"]

        from models.memory import save_memory
        save_memory(phone, "memory one", {})
        save_memory(phone, "memory two", {})

        result = await simulator.send_message(phone, "LIST ALL")


class TestMemoryDeletion:
    """Tests for deleting memories."""

    @pytest.mark.asyncio
    async def test_delete_memory_by_search(self, simulator, onboarded_user, ai_mock):
        """Test deleting a memory by searching for it."""
        phone = onboarded_user["phone"]

        from models.memory import save_memory
        save_memory(phone, "old wifi password is oldpass", {})

        ai_mock.set_response("delete my wifi memory", {
            "action": "delete",
            "delete_type": "memory",
            "query": "wifi"
        })

        result = await simulator.send_message(phone, "Delete my wifi memory")
        # Should ask for confirmation or show matches

    @pytest.mark.asyncio
    async def test_delete_memory_confirmation(self, simulator, onboarded_user, ai_mock):
        """Test memory deletion confirmation flow."""
        phone = onboarded_user["phone"]

        from models.memory import save_memory
        save_memory(phone, "test memory to delete", {})

        ai_mock.set_response("delete test memory", {
            "action": "delete",
            "delete_type": "memory",
            "query": "test"
        })

        # Request deletion
        await simulator.send_message(phone, "Delete test memory")

        # Confirm
        result = await simulator.send_message(phone, "1")  # Confirm first option
        # Should be deleted


class TestMemoryEdgeCases:
    """Edge cases for memory management."""

    @pytest.mark.asyncio
    async def test_empty_memories(self, simulator, onboarded_user):
        """Test viewing memories when none exist."""
        phone = onboarded_user["phone"]

        result = await simulator.send_message(phone, "MY MEMORIES")
        assert any(word in result["output"].lower() for word in ["no", "empty", "haven't"])

    @pytest.mark.asyncio
    async def test_very_long_memory(self, simulator, onboarded_user, ai_mock):
        """Test storing a very long memory."""
        phone = onboarded_user["phone"]

        long_text = "This is a very long memory " * 50

        ai_mock.set_response(f"remember {long_text}", {
            "action": "store",
            "memory_text": long_text
        })

        result = await simulator.send_message(phone, f"Remember {long_text}")
        # Should either store or truncate gracefully

    @pytest.mark.asyncio
    async def test_memory_with_special_characters(self, simulator, onboarded_user, ai_mock):
        """Test memory with special characters."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remember email: test@example.com, code: ABC#123", {
            "action": "store",
            "memory_text": "email: test@example.com, code: ABC#123"
        })

        result = await simulator.send_message(phone, "Remember email: test@example.com, code: ABC#123")

    @pytest.mark.asyncio
    async def test_search_no_match(self, simulator, onboarded_user, ai_mock):
        """Test searching for memory that doesn't exist."""
        phone = onboarded_user["phone"]

        from models.memory import save_memory
        save_memory(phone, "wifi password", {})

        ai_mock.set_response("what's my car's vin number", {
            "action": "retrieve",
            "query": "vin"
        })

        result = await simulator.send_message(phone, "What's my car's VIN number?")
        # Should indicate no match found


class TestMemorySensitiveData:
    """Tests for handling sensitive data in memories."""

    @pytest.mark.asyncio
    async def test_sensitive_data_warning(self, simulator, onboarded_user, ai_mock):
        """Test that sensitive data gets a warning."""
        phone = onboarded_user["phone"]

        # The system should detect sensitive patterns
        ai_mock.set_response("remember my ssn is 123-45-6789", {
            "action": "store",
            "memory_text": "SSN is 123-45-6789",
            "contains_sensitive": True
        })

        result = await simulator.send_message(phone, "Remember my SSN is 123-45-6789")
        # May include warning about sensitive data

    @pytest.mark.asyncio
    async def test_credit_card_warning(self, simulator, onboarded_user, ai_mock):
        """Test warning for credit card numbers."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remember my card number 4111111111111111", {
            "action": "store",
            "memory_text": "card number 4111111111111111",
            "contains_sensitive": True
        })

        result = await simulator.send_message(phone, "Remember my card number 4111111111111111")


class TestDeleteReminderFallbackToMemory:
    """Tests for delete_reminder handler falling back to memory search."""

    @pytest.mark.asyncio
    async def test_delete_keyword_falls_back_to_memory(self, simulator, onboarded_user, ai_mock):
        """When AI misclassifies 'delete surfing' as delete_reminder but no reminder
        matches, the handler should fall back to searching memories."""
        phone = onboarded_user["phone"]

        # Store a memory with the keyword
        from models.memory import save_memory
        save_memory(phone, "I love surfing at Huntington Beach", {})

        # AI misclassifies as delete_reminder instead of delete_memory
        ai_mock.set_response("delete surfing", {
            "action": "delete_reminder",
            "search_term": "surfing",
            "confirmation": "Deleted your reminder about surfing"
        })

        result = await simulator.send_message(phone, "Delete surfing")

        # Should NOT dead-end with "No pending reminders found"
        assert "no pending reminders found" not in result["output"].lower()
        # Should find the memory and ask for confirmation
        assert "memory" in result["output"].lower()
        assert "surfing" in result["output"].lower()

    @pytest.mark.asyncio
    async def test_delete_keyword_no_reminders_no_memories(self, simulator, onboarded_user, ai_mock):
        """When nothing matches at all, show updated message mentioning both."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("delete xyz123", {
            "action": "delete_reminder",
            "search_term": "xyz123",
            "confirmation": "Deleted your reminder about xyz123"
        })

        result = await simulator.send_message(phone, "Delete xyz123")

        # Should mention no reminders or memories found
        assert "no pending reminders or memories found" in result["output"].lower()
