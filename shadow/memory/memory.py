import json
from typing import List, Dict, Any, Optional
from shadow.core.database import get_db_connection

class MemoryEngine:
    def add_memory(self, category: str, content: str, key: Optional[str] = None, tags: Optional[List[str]] = None):
        """
        Store a persistent memory block.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        tags_str = ",".join(tags) if tags else None
        cursor.execute("""
            INSERT INTO memory (category, key, content, tags)
            VALUES (?, ?, ?, ?)
        """, (category, key, content, tags_str))
        conn.commit()
        conn.close()

    def get_memory_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific unique memory configuration/block.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memory WHERE key = ? ORDER BY id DESC LIMIT 1", (key,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def search_memories(self, query: str) -> List[Dict[str, Any]]:
        """
        Keyword search on memory tables contents and tags.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        # Clean basic like query
        like_query = f"%{query}%"
        cursor.execute("""
            SELECT * FROM memory
            WHERE content LIKE ? OR tags LIKE ? OR category LIKE ? OR key LIKE ?
            ORDER BY created_at DESC
        """, (like_query, like_query, like_query, like_query))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_conversation_message(self, session_id: str, role: str, content: str, provider: Optional[str] = None, tokens: int = 0, cost: float = 0.0):
        """
        Store conversation history message.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversation (session_id, role, content, provider, tokens, cost)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, role, content, provider, tokens, cost))
        conn.commit()
        conn.close()

    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieve history for context.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content, provider, tokens, cost, created_at
            FROM conversation
            WHERE session_id = ?
            ORDER BY id ASC LIMIT ?
        """, (session_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def clear_conversation(self, session_id: str):
        """
        Clear logs for session.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversation WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

# Global Memory Singleton
memory_engine = MemoryEngine()
