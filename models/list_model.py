"""
List Model
Handles all list-related database operations
"""

from database import get_db_connection
from config import logger


def create_list(phone_number, list_name):
    """Create a new list for a user"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            'INSERT INTO lists (phone_number, list_name) VALUES (%s, %s) RETURNING id',
            (phone_number, list_name)
        )
        list_id = c.fetchone()[0]
        conn.commit()
        conn.close()
        logger.info(f"Created list '{list_name}' for {phone_number}")
        return list_id
    except Exception as e:
        logger.error(f"Error creating list: {e}")
        return None


def get_lists(phone_number):
    """Get all lists for a user with item counts"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT l.id, l.list_name,
                   COUNT(li.id) as item_count,
                   SUM(CASE WHEN li.completed THEN 1 ELSE 0 END) as completed_count
            FROM lists l
            LEFT JOIN list_items li ON l.id = li.list_id
            WHERE l.phone_number = %s
            GROUP BY l.id, l.list_name
            ORDER BY l.created_at DESC
        ''', (phone_number,))
        results = c.fetchall()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Error getting lists: {e}")
        return []


def get_list_by_name(phone_number, list_name):
    """Find a list by name (case-insensitive)"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            'SELECT id, list_name FROM lists WHERE phone_number = %s AND LOWER(list_name) = LOWER(%s)',
            (phone_number, list_name)
        )
        result = c.fetchone()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error getting list by name: {e}")
        return None


def get_list_by_id(list_id, phone_number):
    """Get a list by ID (with ownership check)"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            'SELECT id, list_name FROM lists WHERE id = %s AND phone_number = %s',
            (list_id, phone_number)
        )
        result = c.fetchone()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error getting list by id: {e}")
        return None


def get_list_items(list_id):
    """Get all items in a list"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            'SELECT id, item_text, completed FROM list_items WHERE list_id = %s ORDER BY created_at',
            (list_id,)
        )
        results = c.fetchall()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Error getting list items: {e}")
        return []


def add_list_item(list_id, phone_number, item_text):
    """Add an item to a list"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            'INSERT INTO list_items (list_id, phone_number, item_text) VALUES (%s, %s, %s) RETURNING id',
            (list_id, phone_number, item_text)
        )
        item_id = c.fetchone()[0]
        conn.commit()
        conn.close()
        logger.info(f"Added item '{item_text}' to list {list_id}")
        return item_id
    except Exception as e:
        logger.error(f"Error adding list item: {e}")
        return None


def mark_item_complete(phone_number, list_name, item_text):
    """Mark an item as complete (case-insensitive match)"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Find the list first
        c.execute(
            'SELECT id FROM lists WHERE phone_number = %s AND LOWER(list_name) = LOWER(%s)',
            (phone_number, list_name)
        )
        list_result = c.fetchone()
        if not list_result:
            conn.close()
            return False

        list_id = list_result[0]
        c.execute(
            '''UPDATE list_items SET completed = TRUE
               WHERE list_id = %s AND LOWER(item_text) = LOWER(%s) AND completed = FALSE''',
            (list_id, item_text)
        )
        updated = c.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    except Exception as e:
        logger.error(f"Error marking item complete: {e}")
        return False


def mark_item_incomplete(phone_number, list_name, item_text):
    """Mark an item as incomplete (case-insensitive match)"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Find the list first
        c.execute(
            'SELECT id FROM lists WHERE phone_number = %s AND LOWER(list_name) = LOWER(%s)',
            (phone_number, list_name)
        )
        list_result = c.fetchone()
        if not list_result:
            conn.close()
            return False

        list_id = list_result[0]
        c.execute(
            '''UPDATE list_items SET completed = FALSE
               WHERE list_id = %s AND LOWER(item_text) = LOWER(%s) AND completed = TRUE''',
            (list_id, item_text)
        )
        updated = c.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    except Exception as e:
        logger.error(f"Error marking item incomplete: {e}")
        return False


def find_item_in_any_list(phone_number, item_text):
    """Find an item across all user's lists (for check off without specifying list)"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT l.id, l.list_name, li.id as item_id, li.item_text
            FROM list_items li
            JOIN lists l ON li.list_id = l.id
            WHERE l.phone_number = %s AND LOWER(li.item_text) = LOWER(%s) AND li.completed = FALSE
        ''', (phone_number, item_text))
        results = c.fetchall()
        conn.close()
        return results
    except Exception as e:
        logger.error(f"Error finding item: {e}")
        return []


def delete_list_item(phone_number, list_name, item_text):
    """Delete an item from a list"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Find the list first
        c.execute(
            'SELECT id FROM lists WHERE phone_number = %s AND LOWER(list_name) = LOWER(%s)',
            (phone_number, list_name)
        )
        list_result = c.fetchone()
        if not list_result:
            conn.close()
            return False

        list_id = list_result[0]
        c.execute(
            'DELETE FROM list_items WHERE list_id = %s AND LOWER(item_text) = LOWER(%s)',
            (list_id, item_text)
        )
        deleted = c.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    except Exception as e:
        logger.error(f"Error deleting list item: {e}")
        return False


def delete_list(phone_number, list_name):
    """Delete an entire list and all its items"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            'DELETE FROM lists WHERE phone_number = %s AND LOWER(list_name) = LOWER(%s)',
            (phone_number, list_name)
        )
        deleted = c.rowcount > 0
        conn.commit()
        conn.close()
        if deleted:
            logger.info(f"Deleted list '{list_name}' for {phone_number}")
        return deleted
    except Exception as e:
        logger.error(f"Error deleting list: {e}")
        return False


def rename_list(phone_number, old_name, new_name):
    """Rename a list"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            '''UPDATE lists SET list_name = %s
               WHERE phone_number = %s AND LOWER(list_name) = LOWER(%s)''',
            (new_name, phone_number, old_name)
        )
        updated = c.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    except Exception as e:
        logger.error(f"Error renaming list: {e}")
        return False


def clear_list(phone_number, list_name):
    """Remove all items from a list (but keep the list)"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        # Find the list first
        c.execute(
            'SELECT id FROM lists WHERE phone_number = %s AND LOWER(list_name) = LOWER(%s)',
            (phone_number, list_name)
        )
        list_result = c.fetchone()
        if not list_result:
            conn.close()
            return False

        list_id = list_result[0]
        c.execute('DELETE FROM list_items WHERE list_id = %s', (list_id,))
        conn.commit()
        conn.close()
        logger.info(f"Cleared all items from list '{list_name}'")
        return True
    except Exception as e:
        logger.error(f"Error clearing list: {e}")
        return False


def get_list_count(phone_number):
    """Get the number of lists a user has"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM lists WHERE phone_number = %s', (phone_number,))
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Error getting list count: {e}")
        return 0


def get_item_count(list_id):
    """Get the number of items in a list"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM list_items WHERE list_id = %s', (list_id,))
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Error getting item count: {e}")
        return 0
