"""
Memory Model
Handles all memory-related database operations
"""

import json
import re
from datetime import datetime
from typing import Any, Optional

from database import get_db_connection, return_db_connection
from config import logger, ENCRYPTION_ENABLED

# Common words to ignore when comparing memory similarity
_STOP_WORDS = frozenset({
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'to', 'of', 'in', 'for',
    'on', 'with', 'at', 'by', 'from', 'as', 'into', 'about', 'that',
    'this', 'it', 'its', 'my', 'your', 'our', 'their', 'his', 'her',
    'and', 'or', 'but', 'not', 'so', 'if', 'than', 'too', 'very',
    'just', 'also', 'i', 'me', 'we', 'you', 'he', 'she', 'they',
    'remember', 'remembered', 'save', 'saved', 'store', 'stored',
})

# Minimum similarity threshold for treating memories as duplicates
_SIMILARITY_THRESHOLD = 0.6


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from memory text, ignoring stop words."""
    words = re.findall(r'[a-z0-9]+', text.lower())
    return {w for w in words if w not in _STOP_WORDS and len(w) > 1}


def _memory_similarity(text_a: str, text_b: str) -> float:
    """Calculate Jaccard similarity between two memory texts based on keywords."""
    keywords_a = _extract_keywords(text_a)
    keywords_b = _extract_keywords(text_b)
    if not keywords_a or not keywords_b:
        return 0.0
    intersection = keywords_a & keywords_b
    union = keywords_a | keywords_b
    return len(intersection) / len(union)


def _find_similar_memory(cursor, phone_number: str, memory_text: str) -> Optional[int]:
    """Find an existing memory with high keyword overlap. Returns the memory ID or None."""
    if ENCRYPTION_ENABLED:
        from utils.encryption import hash_phone
        phone_hash = hash_phone(phone_number)
        cursor.execute(
            'SELECT id, memory_text FROM memories WHERE phone_hash = %s',
            (phone_hash,)
        )
        results = cursor.fetchall()
        if not results:
            cursor.execute(
                'SELECT id, memory_text FROM memories WHERE phone_number = %s',
                (phone_number,)
            )
            results = cursor.fetchall()
    else:
        cursor.execute(
            'SELECT id, memory_text FROM memories WHERE phone_number = %s',
            (phone_number,)
        )
        results = cursor.fetchall()

    best_id = None
    best_score = 0.0
    for mem_id, existing_text in results:
        score = _memory_similarity(memory_text, existing_text)
        if score > best_score:
            best_score = score
            best_id = mem_id

    if best_score >= _SIMILARITY_THRESHOLD:
        return best_id
    return None


def save_memory(phone_number: str, memory_text: str, parsed_data: dict[str, Any]) -> bool:
    """Save a memory, updating an existing similar memory if found.

    Returns True if an existing memory was updated, False if a new one was created.
    """
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Check for existing similar memory to update
        existing_id = _find_similar_memory(c, phone_number, memory_text)

        if existing_id:
            # Update existing memory
            if ENCRYPTION_ENABLED:
                from utils.encryption import encrypt_field
                memory_text_encrypted = encrypt_field(memory_text)
                c.execute(
                    '''UPDATE memories SET memory_text = %s, memory_text_encrypted = %s,
                       parsed_data = %s, created_at = NOW()
                       WHERE id = %s''',
                    (memory_text, memory_text_encrypted, json.dumps(parsed_data), existing_id)
                )
            else:
                c.execute(
                    '''UPDATE memories SET memory_text = %s, parsed_data = %s, created_at = NOW()
                       WHERE id = %s''',
                    (memory_text, json.dumps(parsed_data), existing_id)
                )
            conn.commit()
            logger.info(f"Updated existing memory {existing_id} for user")
            return True
        else:
            # Insert new memory
            if ENCRYPTION_ENABLED:
                from utils.encryption import encrypt_field, hash_phone
                phone_hash = hash_phone(phone_number)
                memory_text_encrypted = encrypt_field(memory_text)
                c.execute(
                    '''INSERT INTO memories (phone_number, phone_hash, memory_text, memory_text_encrypted, parsed_data)
                       VALUES (%s, %s, %s, %s, %s)''',
                    (phone_number, phone_hash, memory_text, memory_text_encrypted, json.dumps(parsed_data))
                )
            else:
                c.execute(
                    'INSERT INTO memories (phone_number, memory_text, parsed_data) VALUES (%s, %s, %s)',
                    (phone_number, memory_text, json.dumps(parsed_data))
                )
            conn.commit()
            logger.info(f"Saved new memory for user")
            return False
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        return False
    finally:
        if conn:
            return_db_connection(conn)

def get_memories(phone_number: str) -> list[tuple[int, str, str, datetime]]:
    """Get all memories for a user"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        if ENCRYPTION_ENABLED:
            from utils.encryption import hash_phone
            phone_hash = hash_phone(phone_number)
            c.execute(
                'SELECT id, memory_text, parsed_data, created_at FROM memories WHERE phone_hash = %s ORDER BY created_at DESC',
                (phone_hash,)
            )
            results = c.fetchall()
            if not results:
                # Fallback for data created before encryption
                c.execute(
                    'SELECT id, memory_text, parsed_data, created_at FROM memories WHERE phone_number = %s ORDER BY created_at DESC',
                    (phone_number,)
                )
                results = c.fetchall()
        else:
            c.execute(
                'SELECT id, memory_text, parsed_data, created_at FROM memories WHERE phone_number = %s ORDER BY created_at DESC',
                (phone_number,)
            )
            results = c.fetchall()

        return results
    except Exception as e:
        logger.error(f"Error getting memories: {e}")
        return []
    finally:
        if conn:
            return_db_connection(conn)

def delete_all_memories(phone_number: str) -> None:
    """Delete all memories for a user"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Delete by both phone_hash and phone_number to catch all records
        if ENCRYPTION_ENABLED:
            from utils.encryption import hash_phone
            phone_hash = hash_phone(phone_number)
            c.execute('DELETE FROM memories WHERE phone_hash = %s OR phone_number = %s', (phone_hash, phone_number))
        else:
            c.execute('DELETE FROM memories WHERE phone_number = %s', (phone_number,))

        conn.commit()
        logger.info(f"Deleted all memories for user")
    except Exception as e:
        logger.error(f"Error deleting memories: {e}")
    finally:
        if conn:
            return_db_connection(conn)


def search_memories(phone_number: str, search_term: str) -> list[tuple[int, str, datetime]]:
    """Search memories by keyword (case-insensitive)"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        search_pattern = f'%{search_term}%'

        if ENCRYPTION_ENABLED:
            from utils.encryption import hash_phone
            phone_hash = hash_phone(phone_number)
            c.execute(
                '''SELECT id, memory_text, created_at FROM memories
                   WHERE phone_hash = %s AND LOWER(memory_text) LIKE LOWER(%s)
                   ORDER BY created_at DESC''',
                (phone_hash, search_pattern)
            )
            results = c.fetchall()
            if not results:
                # Fallback for memories created before encryption
                c.execute(
                    '''SELECT id, memory_text, created_at FROM memories
                       WHERE phone_number = %s AND LOWER(memory_text) LIKE LOWER(%s)
                       ORDER BY created_at DESC''',
                    (phone_number, search_pattern)
                )
                results = c.fetchall()
        else:
            c.execute(
                '''SELECT id, memory_text, created_at FROM memories
                   WHERE phone_number = %s AND LOWER(memory_text) LIKE LOWER(%s)
                   ORDER BY created_at DESC''',
                (phone_number, search_pattern)
            )
            results = c.fetchall()

        return results
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        return []
    finally:
        if conn:
            return_db_connection(conn)


def delete_memory(phone_number: str, memory_id: int) -> bool:
    """Delete a specific memory by ID"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        if ENCRYPTION_ENABLED:
            from utils.encryption import hash_phone
            phone_hash = hash_phone(phone_number)
            # Only delete if it belongs to this user
            c.execute(
                'DELETE FROM memories WHERE id = %s AND phone_hash = %s',
                (memory_id, phone_hash)
            )
            if c.rowcount == 0:
                # Fallback for memories created before encryption
                c.execute(
                    'DELETE FROM memories WHERE id = %s AND phone_number = %s',
                    (memory_id, phone_number)
                )
        else:
            c.execute(
                'DELETE FROM memories WHERE id = %s AND phone_number = %s',
                (memory_id, phone_number)
            )

        deleted = c.rowcount > 0
        conn.commit()
        if deleted:
            logger.info(f"Deleted memory {memory_id}")
        return deleted
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        return False
    finally:
        if conn:
            return_db_connection(conn)
