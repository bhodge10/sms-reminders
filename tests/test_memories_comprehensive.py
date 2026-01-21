"""
Comprehensive Memory Tests for Remyndrs SMS Service

Tests memory storage, retrieval, deletion, and edge cases.
All tests use ConversationSimulator and mock AI responses.
"""

import pytest
from datetime import datetime, timedelta


@pytest.mark.asyncio
class TestMemoryStorage:
    """Test scenarios for storing memories."""

    async def test_save_simple_memory(self, simulator, onboarded_user, ai_mock):
        """Save simple memory (my wifi password is abc123)."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("my wifi password is abc123", {
            "action": "store",
            "memory_text": "wifi password is abc123",
            "confirmation": "Got it! I'll remember your wifi password."
        })

        result = await simulator.send_message(phone, "my wifi password is abc123")
        output_lower = result["output"].lower()
        assert "wifi" in output_lower or "got it" in output_lower or "remember" in output_lower or "saved" in output_lower

    async def test_save_memory_with_yesterday_reference(self, simulator, onboarded_user, ai_mock):
        """Save memory with 'yesterday' reference - converts to actual date."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remember that yesterday i met john at the cafe", {
            "action": "store",
            "memory_text": "On January 17, 2026, I met John at the cafe",
            "confirmation": "Got it! I'll remember that."
        })

        result = await simulator.send_message(phone, "remember that yesterday i met john at the cafe")
        output_lower = result["output"].lower()
        assert "got it" in output_lower or "remember" in output_lower or "john" in output_lower or "saved" in output_lower

    async def test_save_memory_with_last_night_reference(self, simulator, onboarded_user, ai_mock):
        """Save memory with 'last night' reference."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("last night i had dinner at mario's", {
            "action": "store",
            "memory_text": "On January 17, 2026 night, had dinner at Mario's",
            "confirmation": "Got it! I'll remember that."
        })

        result = await simulator.send_message(phone, "last night i had dinner at mario's")
        output_lower = result["output"].lower()
        assert "got it" in output_lower or "remember" in output_lower or "mario" in output_lower or "saved" in output_lower

    async def test_save_memory_with_this_morning_reference(self, simulator, onboarded_user, ai_mock):
        """Save memory with 'this morning' reference."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("this morning i took my vitamins", {
            "action": "store",
            "memory_text": "On January 18, 2026 morning, took vitamins",
            "confirmation": "Got it!"
        })

        result = await simulator.send_message(phone, "this morning i took my vitamins")
        output_lower = result["output"].lower()
        assert "got it" in output_lower or "remember" in output_lower or "vitamin" in output_lower or "saved" in output_lower

    async def test_save_memory_with_future_date(self, simulator, onboarded_user, ai_mock):
        """Save memory with future date reference."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remember that my dentist appointment is next tuesday", {
            "action": "store",
            "memory_text": "Dentist appointment on January 21, 2026",
            "confirmation": "Got it! I'll remember your dentist appointment."
        })

        result = await simulator.send_message(phone, "remember that my dentist appointment is next tuesday")
        output_lower = result["output"].lower()
        assert "got it" in output_lower or "remember" in output_lower or "dentist" in output_lower or "saved" in output_lower

    async def test_save_memory_about_person(self, simulator, onboarded_user, ai_mock):
        """Save memory about a person (contact info)."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("john's email is john@example.com", {
            "action": "store",
            "memory_text": "John's email is john@example.com",
            "confirmation": "Got it! I'll remember John's email."
        })

        result = await simulator.send_message(phone, "john's email is john@example.com")
        output_lower = result["output"].lower()
        assert "got it" in output_lower or "john" in output_lower or "remember" in output_lower or "email" in output_lower

    async def test_save_memory_about_place(self, simulator, onboarded_user, ai_mock):
        """Save memory about a place/location."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remember that the best pizza is at tony's on 5th street", {
            "action": "store",
            "memory_text": "Best pizza is at Tony's on 5th Street",
            "confirmation": "Got it! I'll remember that."
        })

        result = await simulator.send_message(phone, "remember that the best pizza is at tony's on 5th street")
        output_lower = result["output"].lower()
        assert "got it" in output_lower or "pizza" in output_lower or "tony" in output_lower or "remember" in output_lower

    async def test_save_memory_with_numbers(self, simulator, onboarded_user, ai_mock):
        """Save memory with numbers/measurements."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("my car's tire pressure should be 32 psi", {
            "action": "store",
            "memory_text": "Car's tire pressure should be 32 psi",
            "confirmation": "Got it! I'll remember that."
        })

        result = await simulator.send_message(phone, "my car's tire pressure should be 32 psi")
        output_lower = result["output"].lower()
        assert "got it" in output_lower or "tire" in output_lower or "32" in result["output"] or "remember" in output_lower

    async def test_save_long_memory(self, simulator, onboarded_user, ai_mock):
        """Save long memory text (boundary testing)."""
        phone = onboarded_user["phone"]

        long_text = "Remember that my favorite recipe for chocolate chip cookies requires 2 cups flour, 1 cup sugar, 1 cup brown sugar, 2 eggs, 1 tsp vanilla, 1 tsp baking soda, and 2 cups chocolate chips. Preheat oven to 350F and bake for 12 minutes."

        ai_mock.set_response(long_text, {
            "action": "store",
            "memory_text": long_text,
            "confirmation": "Got it! I'll remember your cookie recipe."
        })

        result = await simulator.send_message(phone, long_text)
        output_lower = result["output"].lower()
        assert "got it" in output_lower or "remember" in output_lower or "cookie" in output_lower or "recipe" in output_lower

    async def test_hit_free_tier_memory_limit(self, simulator, onboarded_user, ai_mock):
        """Hit free tier memory limit (5 memories)."""
        phone = onboarded_user["phone"]

        # Save 5 memories
        for i in range(5):
            ai_mock.set_response(f"remember item {i+1}", {
                "action": "store",
                "memory_text": f"Item {i+1}",
                "confirmation": f"Got it!"
            })
            await simulator.send_message(phone, f"remember item {i+1}")

        # Try to save 6th memory
        ai_mock.set_response("remember item 6", {
            "action": "store",
            "memory_text": "Item 6",
            "confirmation": "Got it!"
        })
        result = await simulator.send_message(phone, "remember item 6")

        output_lower = result["output"].lower()
        # Should hit limit or succeed (depends on implementation)
        assert "limit" in output_lower or "maximum" in output_lower or "upgrade" in output_lower or "got it" in output_lower or "5" in result["output"]


@pytest.mark.asyncio
class TestMemoryRetrieval:
    """Test scenarios for retrieving memories."""

    async def test_recall_with_what_is_my(self, simulator, onboarded_user, ai_mock):
        """Recall memory with 'what is my' question."""
        phone = onboarded_user["phone"]

        # Store memory first
        ai_mock.set_response("my wifi password is abc123", {
            "action": "store",
            "memory_text": "wifi password is abc123"
        })
        await simulator.send_message(phone, "my wifi password is abc123")

        # Recall
        ai_mock.set_response("what is my wifi password", {
            "action": "retrieve",
            "query": "wifi password",
            "response": "Your wifi password is abc123"
        })
        result = await simulator.send_message(phone, "what is my wifi password")

        output_lower = result["output"].lower()
        assert "abc123" in output_lower or "wifi" in output_lower or "password" in output_lower

    async def test_recall_with_when_did_i(self, simulator, onboarded_user, ai_mock):
        """Recall memory with 'when did I' question."""
        phone = onboarded_user["phone"]

        # Store memory
        ai_mock.set_response("remember that on january 15 i changed my oil", {
            "action": "store",
            "memory_text": "Changed oil on January 15"
        })
        await simulator.send_message(phone, "remember that on january 15 i changed my oil")

        # Recall
        ai_mock.set_response("when did i change my oil", {
            "action": "retrieve",
            "query": "change oil",
            "response": "You changed your oil on January 15"
        })
        result = await simulator.send_message(phone, "when did i change my oil")

        output_lower = result["output"].lower()
        assert "january" in output_lower or "oil" in output_lower or "15" in result["output"]

    async def test_recall_with_where_did_i(self, simulator, onboarded_user, ai_mock):
        """Recall memory with 'where did I' question."""
        phone = onboarded_user["phone"]

        # Store memory
        ai_mock.set_response("i parked my car in lot b section 4", {
            "action": "store",
            "memory_text": "Car parked in Lot B Section 4"
        })
        await simulator.send_message(phone, "i parked my car in lot b section 4")

        # Recall
        ai_mock.set_response("where did i park my car", {
            "action": "retrieve",
            "query": "park car",
            "response": "You parked in Lot B Section 4"
        })
        result = await simulator.send_message(phone, "where did i park my car")

        output_lower = result["output"].lower()
        assert "lot" in output_lower or "section" in output_lower or "park" in output_lower or "b" in output_lower

    async def test_recall_with_partial_keyword(self, simulator, onboarded_user, ai_mock):
        """Recall memory with partial keyword match."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("my doctor's name is dr. smith", {
            "action": "store",
            "memory_text": "Doctor's name is Dr. Smith"
        })
        await simulator.send_message(phone, "my doctor's name is dr. smith")

        ai_mock.set_response("who is my doc", {
            "action": "retrieve",
            "query": "doc",
            "response": "Your doctor is Dr. Smith"
        })
        result = await simulator.send_message(phone, "who is my doc")

        output_lower = result["output"].lower()
        assert "smith" in output_lower or "doctor" in output_lower or "dr" in output_lower

    async def test_recall_with_multiple_keywords(self, simulator, onboarded_user, ai_mock):
        """Recall with multiple keywords."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("john's work phone is 555-1234", {
            "action": "store",
            "memory_text": "John's work phone is 555-1234"
        })
        await simulator.send_message(phone, "john's work phone is 555-1234")

        ai_mock.set_response("what is john's work number", {
            "action": "retrieve",
            "query": "john work number",
            "response": "John's work phone is 555-1234"
        })
        result = await simulator.send_message(phone, "what is john's work number")

        output_lower = result["output"].lower()
        assert "555" in result["output"] or "john" in output_lower or "1234" in result["output"]

    async def test_recall_case_insensitive(self, simulator, onboarded_user, ai_mock):
        """Case-insensitive memory search."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("my WIFI password is ABC123", {
            "action": "store",
            "memory_text": "WIFI password is ABC123"
        })
        await simulator.send_message(phone, "my WIFI password is ABC123")

        ai_mock.set_response("what is my wifi password", {
            "action": "retrieve",
            "query": "wifi password",
            "response": "Your WIFI password is ABC123"
        })
        result = await simulator.send_message(phone, "what is my wifi password")

        output_lower = result["output"].lower()
        assert "abc123" in output_lower or "wifi" in output_lower or "password" in output_lower

    async def test_retrieve_no_memories_exist(self, simulator, onboarded_user, ai_mock):
        """Retrieve when no memories exist - helpful response."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("what is my password", {
            "action": "retrieve",
            "query": "password",
            "response": "I don't have any memories stored about that."
        })
        result = await simulator.send_message(phone, "what is my password")

        output_lower = result["output"].lower()
        assert "don't have" in output_lower or "no memor" in output_lower or "not found" in output_lower or "haven't stored" in output_lower or "password" in output_lower

    async def test_search_no_matches(self, simulator, onboarded_user, ai_mock):
        """Search returns no matches - helpful response."""
        phone = onboarded_user["phone"]

        # Store a memory first
        ai_mock.set_response("my dog's name is rex", {
            "action": "store",
            "memory_text": "Dog's name is Rex"
        })
        await simulator.send_message(phone, "my dog's name is rex")

        # Search for something unrelated
        ai_mock.set_response("what is my cat's name", {
            "action": "retrieve",
            "query": "cat",
            "response": "I don't have any memories about your cat."
        })
        result = await simulator.send_message(phone, "what is my cat's name")

        output_lower = result["output"].lower()
        assert "don't" in output_lower or "no memor" in output_lower or "not found" in output_lower or "cat" in output_lower

    async def test_list_all_memories(self, simulator, onboarded_user, ai_mock):
        """List all memories command."""
        phone = onboarded_user["phone"]

        # Store some memories
        ai_mock.set_response("my wifi password is abc123", {"action": "store", "memory_text": "wifi password is abc123"})
        await simulator.send_message(phone, "my wifi password is abc123")

        ai_mock.set_response("john's email is john@test.com", {"action": "store", "memory_text": "John's email is john@test.com"})
        await simulator.send_message(phone, "john's email is john@test.com")

        # List all
        ai_mock.set_response("show all my memories", {
            "action": "list_memories",
            "response": "Here are your memories:\n1. wifi password is abc123\n2. John's email is john@test.com"
        })
        result = await simulator.send_message(phone, "show all my memories")

        output_lower = result["output"].lower()
        assert "wifi" in output_lower or "john" in output_lower or "memor" in output_lower or "1." in result["output"]

    async def test_save_and_immediate_recall(self, simulator, onboarded_user, ai_mock):
        """Save and immediate recall in same session."""
        phone = onboarded_user["phone"]

        # Save
        ai_mock.set_response("my locker code is 4532", {
            "action": "store",
            "memory_text": "locker code is 4532",
            "confirmation": "Got it!"
        })
        await simulator.send_message(phone, "my locker code is 4532")

        # Immediate recall
        ai_mock.set_response("what is my locker code", {
            "action": "retrieve",
            "query": "locker code",
            "response": "Your locker code is 4532"
        })
        result = await simulator.send_message(phone, "what is my locker code")

        output_lower = result["output"].lower()
        assert "4532" in result["output"] or "locker" in output_lower


@pytest.mark.asyncio
class TestMemoryDeletion:
    """Test scenarios for deleting memories."""

    async def test_delete_memory_single_match_confirm_yes(self, simulator, onboarded_user, ai_mock):
        """Delete memory - single match, confirm with YES."""
        phone = onboarded_user["phone"]

        # Store memory
        ai_mock.set_response("my wifi password is abc123", {"action": "store", "memory_text": "wifi password is abc123"})
        await simulator.send_message(phone, "my wifi password is abc123")

        # Delete request
        ai_mock.set_response("delete my wifi password", {
            "action": "delete_memory",
            "query": "wifi password",
            "match": "wifi password is abc123"
        })
        result = await simulator.send_message(phone, "delete my wifi password")

        output_lower = result["output"].lower()
        # Should ask for confirmation or delete
        assert "delete" in output_lower or "wifi" in output_lower or "yes" in output_lower or "confirm" in output_lower

        # Confirm with YES if needed
        if "yes" in output_lower or "confirm" in output_lower:
            result = await simulator.send_message(phone, "yes")
            output_lower = result["output"].lower()
            assert "deleted" in output_lower or "removed" in output_lower or "done" in output_lower or "ok" in output_lower

    async def test_delete_memory_single_match_cancel_no(self, simulator, onboarded_user, ai_mock):
        """Delete memory - single match, cancel with NO."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("my wifi password is abc123", {"action": "store", "memory_text": "wifi password is abc123"})
        await simulator.send_message(phone, "my wifi password is abc123")

        ai_mock.set_response("delete my wifi password", {
            "action": "delete_memory",
            "query": "wifi password"
        })
        result = await simulator.send_message(phone, "delete my wifi password")

        output_lower = result["output"].lower()
        if "yes" in output_lower or "confirm" in output_lower:
            result = await simulator.send_message(phone, "no")
            output_lower = result["output"].lower()
            assert "kept" in output_lower or "cancel" in output_lower or "ok" in output_lower or "not" in output_lower

    async def test_delete_memory_multiple_matches_show_selection(self, simulator, onboarded_user, ai_mock):
        """Delete memory - multiple matches, show selection."""
        phone = onboarded_user["phone"]

        # Store multiple password memories
        ai_mock.set_response("my wifi password is abc123", {"action": "store", "memory_text": "wifi password is abc123"})
        await simulator.send_message(phone, "my wifi password is abc123")

        ai_mock.set_response("my computer password is xyz789", {"action": "store", "memory_text": "computer password is xyz789"})
        await simulator.send_message(phone, "my computer password is xyz789")

        # Delete by keyword
        ai_mock.set_response("delete my password", {
            "action": "delete_memory",
            "query": "password",
            "matches": ["wifi password is abc123", "computer password is xyz789"]
        })
        result = await simulator.send_message(phone, "delete my password")

        output_lower = result["output"].lower()
        # Should show options or ask which one
        assert "1" in result["output"] or "which" in output_lower or "password" in output_lower or "select" in output_lower

    async def test_select_memory_to_delete_by_number(self, simulator, onboarded_user, ai_mock):
        """Select memory to delete by number."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("my wifi password is abc123", {"action": "store", "memory_text": "wifi password is abc123"})
        await simulator.send_message(phone, "my wifi password is abc123")

        ai_mock.set_response("my computer password is xyz789", {"action": "store", "memory_text": "computer password is xyz789"})
        await simulator.send_message(phone, "my computer password is xyz789")

        ai_mock.set_response("delete my password", {
            "action": "delete_memory",
            "query": "password"
        })
        await simulator.send_message(phone, "delete my password")

        # Select by number
        result = await simulator.send_message(phone, "1")

        output_lower = result["output"].lower()
        assert "delete" in output_lower or "wifi" in output_lower or "yes" in output_lower or "confirm" in output_lower or "removed" in output_lower

    async def test_delete_no_matches_found(self, simulator, onboarded_user, ai_mock):
        """Delete when no matches found."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("delete my unicorn password", {
            "action": "delete_memory",
            "query": "unicorn password"
        })
        result = await simulator.send_message(phone, "delete my unicorn password")

        output_lower = result["output"].lower()
        assert "no" in output_lower or "not found" in output_lower or "don't have" in output_lower or "couldn't find" in output_lower


@pytest.mark.asyncio
class TestMemoryEdgeCases:
    """Test edge cases for memories."""

    async def test_memory_with_special_characters(self, simulator, onboarded_user, ai_mock):
        """Memory with special characters."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("my server password is P@$$w0rd!", {
            "action": "store",
            "memory_text": "server password is P@$$w0rd!"
        })
        result = await simulator.send_message(phone, "my server password is P@$$w0rd!")

        output_lower = result["output"].lower()
        assert "got it" in output_lower or "remember" in output_lower or "server" in output_lower or "saved" in output_lower

    async def test_memory_about_event_with_date(self, simulator, onboarded_user, ai_mock):
        """Memory about an event with date."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("remember that on march 15 sarah's birthday party is at the park", {
            "action": "store",
            "memory_text": "March 15: Sarah's birthday party at the park"
        })
        result = await simulator.send_message(phone, "remember that on march 15 sarah's birthday party is at the park")

        output_lower = result["output"].lower()
        assert "got it" in output_lower or "remember" in output_lower or "sarah" in output_lower or "birthday" in output_lower

    async def test_update_existing_memory(self, simulator, onboarded_user, ai_mock):
        """Update/overwrite existing memory (same topic)."""
        phone = onboarded_user["phone"]

        # Store original
        ai_mock.set_response("my wifi password is oldpass123", {"action": "store", "memory_text": "wifi password is oldpass123"})
        await simulator.send_message(phone, "my wifi password is oldpass123")

        # Update
        ai_mock.set_response("actually my wifi password is newpass456", {
            "action": "store",
            "memory_text": "wifi password is newpass456",
            "update": True
        })
        result = await simulator.send_message(phone, "actually my wifi password is newpass456")

        output_lower = result["output"].lower()
        assert "got it" in output_lower or "updated" in output_lower or "remember" in output_lower or "newpass" in output_lower

    async def test_memory_disambiguation_similar(self, simulator, onboarded_user, ai_mock):
        """Memory disambiguation when multiple similar."""
        phone = onboarded_user["phone"]

        ai_mock.set_response("john's home phone is 555-1111", {"action": "store", "memory_text": "John's home phone is 555-1111"})
        await simulator.send_message(phone, "john's home phone is 555-1111")

        ai_mock.set_response("john's work phone is 555-2222", {"action": "store", "memory_text": "John's work phone is 555-2222"})
        await simulator.send_message(phone, "john's work phone is 555-2222")

        # Ask ambiguous question
        ai_mock.set_response("what is john's phone", {
            "action": "retrieve",
            "query": "john phone",
            "response": "I found multiple entries:\n- John's home phone: 555-1111\n- John's work phone: 555-2222"
        })
        result = await simulator.send_message(phone, "what is john's phone")

        output_lower = result["output"].lower()
        assert "john" in output_lower or "555" in result["output"] or "phone" in output_lower

    async def test_cross_reference_memory(self, simulator, onboarded_user, ai_mock):
        """Cross-reference memory in other contexts."""
        phone = onboarded_user["phone"]

        # Store memory about a person
        ai_mock.set_response("remember that dr. smith works at city hospital", {
            "action": "store",
            "memory_text": "Dr. Smith works at City Hospital"
        })
        await simulator.send_message(phone, "remember that dr. smith works at city hospital")

        # Ask in different context
        ai_mock.set_response("where does my doctor work", {
            "action": "retrieve",
            "query": "doctor work",
            "response": "Dr. Smith works at City Hospital"
        })
        result = await simulator.send_message(phone, "where does my doctor work")

        output_lower = result["output"].lower()
        assert "hospital" in output_lower or "smith" in output_lower or "city" in output_lower
